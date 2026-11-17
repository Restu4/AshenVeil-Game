#!/usr/bin/env python3
"""ASHEN VEIL - player sprite sheet generator (64x64 frames, Godot 4 ready)."""
import math, json, os
from PIL import Image, ImageOps

FW = FH = 64
CX, BASE = 32, 52
COLS = 8

def H(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ---- limited palette: charcoal, dark gray, muted purple, desaturated brown, glowing white
OUT=H('0b0a0e'); C0=H('15131b'); C1=H('232030'); C2=H('353048'); C3=H('4d4863')
P1=H('4a3a5e'); P2=H('6f5a8f')
B0=H('3a2e28'); B1=H('6b584a'); B2=H('8f7a68')
G1=H('565366'); G2=H('858297'); G3=H('b4b1c6')
W=H('f6f6ff'); HALO=H('9c98c8'); FACE=H('040307')
CP0=H('16131e'); CP1=H('252035'); CP2=H('45375e')
SH0=H('3f3633'); SH1=H('5a4e48')
LEG=H('4a455a'); LEGD=H('332f40'); HAND=H('1c1a24')
TR_A=H('3f3560'); TR_B=H('6a5c94'); TR_C=H('aaa3cf')

class Cv:
    def __init__(s):
        s.im = Image.new('RGBA', (FW, FH), (0,0,0,0)); s.p = s.im.load()
    def px(s, x, y, c):
        x = int(math.floor(x+0.5)); y = int(math.floor(y+0.5))
        if 0 <= x < FW and 0 <= y < FH: s.p[x, y] = tuple(c)+(255,)
    def rect(s, x0, y0, x1, y1, c):
        for y in range(int(y0), int(y1)+1):
            for x in range(int(x0), int(x1)+1): s.px(x, y, c)
    def line(s, x0, y0, x1, y1, c):
        n = int(max(abs(x1-x0), abs(y1-y0)))
        for i in range(n+1):
            t = i/n if n else 0
            s.px(x0+(x1-x0)*t, y0+(y1-y0)*t, c)

class Rg:
    def __init__(s, cv, ox, oy): s.cv, s.ox, s.oy = cv, ox, oy
    def P(s, x, y, c): s.cv.px(s.ox+x, s.oy+y, c)
    def R(s, x0, y0, x1, y1, c): s.cv.rect(s.ox+x0, s.oy+y0, s.ox+x1, s.oy+y1, c)
    def L(s, x0, y0, x1, y1, c): s.cv.line(s.ox+x0, s.oy+y0, s.ox+x1, s.oy+y1, c)

SWORD_LEN = 29
def sword(rg, p0, p1, bands=()):
    x0, y0 = p0; x1, y1 = p1
    L = math.hypot(x1-x0, y1-y0); ux, uy = (x1-x0)/L, (y1-y0)/L
    th = (1,0) if abs(uy) >= abs(ux) else (0,1)
    pr = (-uy, ux)
    for i in range(int(L*2)+1):
        t = i/2; x = x0+ux*t; y = y0+uy*t
        if t < 1.5:
            rg.P(x, y, G2); rg.P(x+th[0], y+th[1], G1)
        elif t < 5.5:
            rg.P(x, y, B2 if int(t) % 2 else B1)
        elif t < 7:
            for k in range(-3, 4): rg.P(x+pr[0]*k, y+pr[1]*k, B2 if k <= 0 else B1)
        elif t > L-3:
            rg.P(x, y, G3 if t > L-1.5 else G2)
        else:
            rg.P(x-th[0], y-th[1], G3); rg.P(x, y, G2); rg.P(x+th[0], y+th[1], G1)
    for tb in bands:
        x = x0+ux*tb; y = y0+uy*tb
        for k in (-2,-1,0,1,2,3):
            rg.P(x+pr[0]*k, y+pr[1]*k, B1 if k < 2 else B0)

def trail(rg, hand, a0, a1):
    n = max(int(abs(a1-a0)*2), 1)
    for i in range(n+1):
        f = i/n
        a = math.radians(a0+(a1-a0)*f)
        th = 1+int(f**1.5*11)
        r = 23.0
        while r > 23-th:
            col = TR_A if f < 0.5 else TR_B
            if r > 22.2 and f > 0.3: col = TR_C
            elif r < 23-th+1.2 and f > 0.6: col = TR_A
            rg.P(hand[0]+math.cos(a)*r, hand[1]+math.sin(a)*r, col)
            r -= 0.5

def arm_line(rg, s, e):
    n = int(max(abs(e[0]-s[0]), abs(e[1]-s[1]), 1))
    th = (1,0) if abs(e[1]-s[1]) >= abs(e[0]-s[0]) else (0,1)
    for i in range(n+1):
        x = s[0]+(e[0]-s[0])*i/n; y = s[1]+(e[1]-s[1])*i/n
        rg.P(x-th[0], y-th[1], C2); rg.P(x, y, C1); rg.P(x+th[0], y+th[1], C0)
    rg.R(round(e[0])-1, round(e[1])-1, round(e[0]), round(e[1]), HAND)

def held_sword(rg, sw, shoulder):
    hand, ang, tr = sw
    if tr is not None: trail(rg, hand, tr, ang)
    a = math.radians(ang); u = (math.cos(a), math.sin(a))
    p0 = (hand[0]-u[0]*4, hand[1]-u[1]*4)
    p1 = (p0[0]+u[0]*SWORD_LEN, p0[1]+u[1]*SWORD_LEN)
    sword(rg, p0, p1)
    arm_line(rg, shoulder, hand)

def cape_front(rg, ytop, ybot, hw0, hw1, sway):
    if ybot <= ytop+2: ybot = ytop+3
    for y in range(ytop, ybot+1):
        t = (y-ytop)/(ybot-ytop)
        hw = round(hw0+(hw1-hw0)*t); sh = round(sway*t*t)
        x0, x1 = -hw+sh, hw+sh
        for x in range(x0, x1+1):
            if y == ybot and (x-sh) % 3 == 0: continue
            if y == ybot-1 and (x-sh) % 5 == 0: continue
            c = CP1
            if x == x0: c = CP2
            elif x >= x1-1: c = CP0
            elif (x-sh+hw) % 5 == 0: c = CP0
            elif (x-sh+hw) % 5 == 2 and y < ybot-2: c = CP2 if t < 0.5 else CP1
            rg.P(x, y, c)

def put_eye(rg, pts, face):
    S = set(pts)
    for (x, y) in pts: rg.P(x, y, W)
    for (x, y) in pts:
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            q = (x+dx, y+dy)
            if q not in S and q in face: rg.P(q[0], q[1], HALO)

# ------------------------------------------------------------------ FRONT / BACK
def hood_front(h, back):
    rows = {-31:3, -30:5, -29:6, -28:7}
    for y in range(-27, -18): rows[y] = 7
    rows[-18] = 8; rows[-17] = 7
    for y, hw in rows.items():
        h.R(-hw, y, hw, y, C2)
        h.P(-hw, y, C3)
        if hw >= 6: h.P(-hw+1, y, C3 if y < -23 else C2)
        h.P(hw, y, C0)
        if hw >= 6: h.P(hw-1, y, C1)
    h.R(-2, -31, 1, -31, C3); h.R(-3, -30, 0, -30, C3)
    h.R(-7, -17, 7, -17, C0)
    if not back:
        fh = {-27:3, -26:4, -25:5, -24:5, -23:5, -22:5, -21:4, -20:3}
        for y in range(-28, -18):
            hw = fh.get(y, 2)+1; h.R(-hw, y, hw, y, P1)
        face = set()
        for y, hw in fh.items():
            h.R(-hw, y, hw, y, FACE)
            for x in range(-hw, hw+1): face.add((x, y))
        put_eye(h, [(1,-24),(2,-24),(3,-24),(3,-23)], face)   # character's LEFT eye = viewer's right
    else:
        h.R(0, -30, 0, -19, C0); h.R(-1, -30, -1, -25, C3)
        h.R(-4, -24, -4, -20, C1); h.R(4, -26, 4, -20, C0)
        h.R(-1, -18, 0, -18, P2)

def draw_front(cv, p, back=False):
    dx, dy = p.get('dx', 0), p.get('dy', 0)
    ox, oy = CX+dx, BASE+dy
    gx = CX+p.get('gx', dx)
    r = Rg(cv, ox, oy); h = Rg(cv, ox+p.get('hx',0), oy+p.get('hy',0))
    held = p.get('sw') is not None
    arm = p.get('arm')
    ybot = -3-dy
    sh_arm = (5,-17) if not back else (6,-17)

    def legs():
        for side, lift in ((-1, p.get('ll',0)), (1, p.get('rl',0))):
            sx0, sx1 = (-5,-1) if side < 0 else (1,5)
            kx0, kx1 = (-4,-2) if side < 0 else (2,4)
            r.R(sx0, -9, sx1, -7, SH1); r.R(sx0, -7, sx1, -7, SH0)
            top, bot = oy-6, BASE-3-lift
            if bot >= top:
                cv.rect(gx+kx0, top, gx+kx1, bot, LEG)
                cv.rect(gx+kx1, top, gx+kx1, bot, LEGD)
            a, b = (-5,-2) if side < 0 else (2,5)
            cv.rect(gx+a, BASE-2-lift, gx+b, BASE-2-lift, B1)
            cv.rect(gx+a, BASE-1-lift, gx+b, BASE-1-lift, B0)
            cv.px(gx+(a if side<0 else b), BASE-1-lift, B1)
    def torso():
        for y in range(-19, -9):
            hw = 6 if y <= -14 else 7
            r.R(-hw, y, hw, y, C1); r.P(-hw, y, C2)
            if y < -12: r.P(-hw+1, y, C2)
            r.P(hw, y, C0); r.P(hw-1, y, C0)
        r.R(-7, -10, 7, -10, C0)
    def sleeves():
        la, ra = p.get('la',0), p.get('ra',0)
        for side, a in ((-1, la), (1, ra)):
            if arm and side == 1: continue
            x0, x1 = (-9,-7) if side < 0 else (7,9)
            r.R(x0, -18+a, x1, -11+a, C1)
            r.R(x0, -18+a, x0, -11+a, C2 if side < 0 else C1)
            r.R(x1, -18+a, x1, -11+a, C0)
            r.R(x0, -11+a, x1, -11+a, C0)
            r.R(x0+1, -10+a, x1-1, -9+a, HAND)

    if not back:
        if not held and not arm_back(p): pass
        cape_front(r, -19, ybot, 6, 10, p.get('sway',0))
        if not held: sword(r, (-11,-28), (10,-7), bands=(12,18))
        legs(); torso(); sleeves()
        r.R(-4,-14,4,-14,C0); r.R(-4,-13,-4,-11,C0); r.R(4,-13,4,-11,C0)
        r.L(-6,-18,6,-10,B1); r.L(-6,-17,6,-9,B0)
        r.R(-1,-14,0,-13,B2)
        for yy in range(-16,-12): r.P(-2,yy,G1)
        for yy in range(-16,-11): r.P(2,yy,G1)
        r.P(-2,-12,G3); r.P(2,-11,G3)
        hood_front(h, False)
        if held:
            held_sword(r, p['sw'], sh_arm)
        elif arm:
            arm_line(r, arm[0], arm[1])
    else:
        legs(); torso(); 
        cape_front(r, -19, ybot, 6, 9, p.get('sway',0))
        sleeves()
        if held:
            held_sword(r, p['sw'], sh_arm)
        else:
            sword(r, (11,-28), (-10,-7), bands=(12,18))
            if arm: arm_line(r, arm[0], arm[1])
        hood_front(h, True)

def arm_back(p): return False

# ------------------------------------------------------------------ SIDE (faces LEFT)
def hood_side(h):
    edges = {-31:(-3,3), -30:(-5,4), -29:(-6,5), -28:(-7,6)}
    for y in range(-27, -19): edges[y] = (-7, 8)
    edges[-19] = (-7, 8); edges[-18] = (-6, 8); edges[-17] = (-5, 7)
    for y, (a, b) in edges.items():
        h.R(a, y, b, y, C2)
        h.P(b, y, C0)
        if b-a > 6: h.P(b-1, y, C1); h.P(b-2, y, C1 if y > -25 else C2)
    h.R(-3, -31, 1, -31, C3); h.R(-4, -30, 0, -30, C3); h.R(-5,-29,-2,-29,C3)
    h.R(-5, -17, 7, -17, C0)
    # face opening at the front
    h.R(-7, -27, -2, -20, P1)
    face = set()
    for y in range(-26, -20):
        h.R(-6, y, -2, y, FACE)
        for x in range(-6, -1): face.add((x, y))
    h.R(-2, -26, -2, -21, C0)
    put_eye(h, [(-5,-24),(-4,-24),(-3,-24),(-3,-23)], face)
    h.R(-6, -19, -3, -19, C1)

def draw_side(cv, p):
    dx, dy = p.get('dx', 0), p.get('dy', 0)
    ox, oy = CX+dx, BASE+dy
    gx = CX+p.get('gx', dx)
    r = Rg(cv, ox, oy); h = Rg(cv, ox+p.get('hx',0), oy+p.get('hy',0))
    held = p.get('sw') is not None; arm = p.get('arm')
    trail_ = p.get('trail',0); amp = p.get('amp',0); wv = p.get('wave',0)
    ybot = -3-dy
    # cape trailing behind (+x)
    for y in range(-19, ybot+1):
        t = (y+19)/max(1, (ybot+19)); w = amp*math.sin(wv+t*4)*t
        x0 = 2+round(trail_*t*0.8+w*0.5)
        x1 = 5+round(3.5*t)+round(trail_*t*1.3+w)
        for x in range(x0, x1+1):
            if y == ybot and x % 3 == 0: continue
            if y == ybot-1 and x % 5 == 0: continue
            c = CP1
            if x >= x1-1: c = CP0
            elif x == x0: c = CP2
            elif (x+y//3) % 4 == 0 and t > 0.25: c = CP0
            r.P(x, y, c)
    if not held: sword(r, (8,-32), (12,-4), bands=(12,19))
    # legs
    for far in (True, False):
        lx = p.get('fx',0) if far else p.get('nx',0)
        lift = p.get('fl',0) if far else p.get('nl',0)
        X = gx+lx
        cv.rect(X-2, oy-9, X+1, oy-7, SH0 if far else SH1)
        top, bot = oy-6, BASE-3-lift
        if bot >= top: cv.rect(X-1, top, X+1, bot, LEGD if far else LEG)
        cv.rect(X-3, BASE-2-lift, X+1, BASE-2-lift, B1)
        cv.rect(X-4, BASE-1-lift, X+1, BASE-1-lift, B0)
        cv.px(X-4, BASE-1-lift, B1)
    # torso
    for y in range(-19, -9):
        a, b = (-5, 5) if y < -12 else (-6, 6)
        r.R(a, y, b, y, C1); r.P(a, y, C2); r.P(a+1, y, C2 if y < -13 else C1)
        r.P(b, y, C0); r.P(b-1, y, C0)
    r.R(-6, -10, 6, -10, C0)
    r.L(-4,-18,4,-11,B1); r.L(-4,-17,4,-10,B0)
    r.R(-5,-14,0,-14,C0); r.R(-5,-13,-5,-11,C0)           # pocket edge
    # near arm
    if not arm and not held:
        ax = p.get('ax',0); ay = p.get('ay',0)
        r.R(ax-2, -18+ay, ax+1, -11+ay, C2)
        r.R(ax-2, -18+ay, ax-2, -11+ay, C0); r.R(ax+1, -18+ay, ax+1, -11+ay, C0)
        r.R(ax-2, -11+ay, ax+1, -11+ay, C0)
        r.R(ax-1, -10+ay, ax, -9+ay, HAND)
    hood_side(h)
    for yy in range(-16, -12): r.P(-5, yy, G1)
    r.P(-5, -12, G3)
    if held: held_sword(r, p['sw'], (-1,-17))
    elif arm: arm_line(r, (-1,-17), arm)

# ------------------------------------------------------------------ DODGE BALL
def draw_ball(cv, d, th, frame):
    cx, cy = CX, BASE-9
    mx, my = {'left':(-1,0), 'right':(1,0), 'down':(0,1), 'up':(0,-1)}[d]
    qx, qy = -my, mx
    g = Rg(cv, cx, cy)
    for k in range(5, 17):
        w = max(0, 3-(k-5)//3); wig = round(math.sin(k*0.7+frame)*1.2)
        for j in range(-w, w+1):
            c = CP2 if j == -w and w > 0 else (CP0 if j == w and w > 0 else CP1)
            g.P(-mx*k+qx*(j+wig), -my*k+qy*(j+wig), c)
    R = 8
    for yy in range(-R, R+1):
        for xx in range(-R, R+1):
            if xx*xx+yy*yy <= R*R+R-2:
                c = C1
                if xx+yy < -R*0.55: c = C2
                elif xx+yy > R*0.7: c = C0
                g.P(xx, yy, c)
    u = (math.cos(th), math.sin(th)); v = (-u[1], u[0])
    for s in (-1, 1):   # sandals + legs
        g.P(-u[0]*6+v[0]*s*2.3, -u[1]*6+v[1]*s*2.3, LEG)
        g.P(-u[0]*7+v[0]*s*2.3, -u[1]*7+v[1]*s*2.3, B1)
        g.P(-u[0]*8+v[0]*s*2.3, -u[1]*8+v[1]*s*2.3, B0)
    def rot(a): 
        c, s = math.cos(a), math.sin(a); return (u[0]*c-u[1]*s, u[0]*s+u[1]*c)
    a = rot(math.radians(25)); b = rot(math.radians(150))
    sword(g, (a[0]*11, a[1]*11), (b[0]*11, b[1]*11))
    hc = (u[0]*6.2, u[1]*6.2)
    for yy in range(-6, 7):
        for xx in range(-6, 7):
            dd = math.hypot(xx, yy)
            if dd <= 4.6: g.P(hc[0]+xx, hc[1]+yy, C2 if dd < 3.9 else P1)
    if d != 'up':
        fc = (u[0]*7.4, u[1]*7.4)
        for yy in range(-3, 4):
            for xx in range(-3, 4):
                if math.hypot(xx, yy) <= 2.6: g.P(fc[0]+xx, fc[1]+yy, FACE)
        e = (fc[0]+v[0]*1.0, fc[1]+v[1]*1.0)
        g.P(e[0], e[1], W); g.P(e[0]+v[0], e[1]+v[1], W)
    # strap hint
    g.P(-v[0]*3, -v[1]*3, B1); g.P(-v[0]*3-u[0], -v[1]*3-u[1], B0)

# ------------------------------------------------------------------ POSES
DIRS = ['down', 'up', 'left', 'right']

def locomotion(d, i, n, run):
    ph = 2*math.pi*i/n; s = math.sin(ph); c = math.cos(ph)
    if d in ('down', 'up'):
        lm = 3 if run else 2
        p = dict(ll=round(lm*max(0, s)), rl=round(lm*max(0, -s)),
                 la=round((3 if run else 2)*s), ra=-round((3 if run else 2)*s),
                 dy=-(2 if run else 1) if abs(s) < 0.5 else 0,
                 sway=round((3 if run else 1.5)*math.sin(ph+1)))
        if run: p['hy'] = 1
        return p
    st = 5 if run else 3
    lm = 3 if run else 2
    p = dict(nx=round(-st*s), fx=round(st*s), nl=round(lm*max(0, c)), fl=round(lm*max(0, -c)),
             ax=round((3 if run else 2.5)*s), dy=-(2 if run else 1) if abs(s) < 0.5 else 0,
             trail=4 if run else 1, amp=2 if run else 1, wave=ph*1.0)
    if run: p['dx'] = -1; p['hx'] = -1; p['gx'] = 0
    return p

def idle_pose(d, i):
    hy = [0, -1, -1, 0][i]
    if d in ('down', 'up'): return dict(hy=hy, sway=[0, 1, 1, 0][i]*(-1 if i == 3 else 1))
    return dict(hy=hy, trail=[0, 0, 1, 0][i], amp=1, wave=i*1.6)

ATK = {
 'left': [dict(dx=1, dy=1, hy=1, arm=(4,-21)),
          dict(dx=1, sw=((3,-23), -62, None)),
          dict(sw=((-2,-24), -112, -62)),
          dict(dx=-1, sw=((-3,-19), -178, -112)),
          dict(dx=-2, hx=-1, sw=((-3,-14), -220, -178)),
          dict(dx=-1, arm=(-2,-12))],
 'down': [dict(dy=1, arm=((5,-17),(6,-24))),
          dict(sw=((3,-24), -102, None)),
          dict(sw=((2,-25), -55, -102)),
          dict(sw=((1,-20), 0, -55)),
          dict(sw=((3,-15), 50, 0)),
          dict(arm=((5,-17),(3,-12)))],
 'up':   [dict(dy=1, arm=((6,-17),(6,-23))),
          dict(sw=((5,-24), -22, None)),
          dict(sw=((4,-26), -65, -22)),
          dict(sw=((1,-27), -115, -65)),
          dict(sw=((-3,-24), -165, -115)),
          dict(arm=((6,-17),(-5,-16)))],
}
def attack_pose(d, i):
    p = dict(ATK['left' if d == 'right' else d][i])
    if 'sw' in p:
        hand, ang, tr = p['sw']
        sh = {'left':(-1,-17), 'down':(5,-17), 'up':(6,-17)}['left' if d == 'right' else d]
        p['sw'] = (hand, ang, tr)
    if 'arm' in p and d in ('down', 'up'): pass
    if 'arm' in p and d in ('left', 'right'): pass
    if d in ('left','right') and 'sway' not in p: p.update(trail=2+(i in (3,4))*2, amp=1, wave=i)
    if d in ('down','up'): p['sway'] = [0,1,-1,-2,-1,0][i]
    return p

def dodge_pose(d, i):
    if i == 0:  p = dict(dy=3, hy=1)
    elif i == 1: p = dict(dy=4, hy=2)
    elif i in (2, 3, 4):
        sgn = -1 if d == 'left' else 1
        return dict(ball=math.radians(-90 + sgn*[100, 215, 330][i-2]))
    else:       p = dict(dy=2, hy=1)
    mv = {'left':(-1,0), 'right':(1,0), 'down':(0,0), 'up':(0,0)}[d]
    if d in ('left', 'right'):
        p.update(dx=-1 if i < 2 else 0, hx=-1, trail=3, amp=1, wave=i)
    else:
        p.update(sway=-2 if i < 2 else 0)
    return p

def hurt_pose(d, i):
    if d in ('down', 'up'):
        return [dict(flash=True, hy=-1, la=-2, ra=-2, sway=2, dy=0),
                dict(dy=-1, hy=-2, la=-2, ra=-2, sway=-3),
                dict(hy=0, la=1, ra=1, sway=1)][i]
    return [dict(flash=True, dx=2, gx=1, hx=1, trail=3, amp=1, wave=1),
            dict(dx=3, gx=2, hx=2, trail=4, amp=1, wave=2),
            dict(dx=1, gx=1, hx=0, trail=2, amp=1, wave=3)][i]

DEATH_ANG = [0, 6, 16, 32, 52, 72, 88, 90]
def death_pose(i):
    base = [dict(flash=True, dx=1, hy=-1, la=-2, ra=-2, sway=2),
            dict(dx=2, hy=-1, la=-3, ra=-3, sway=-2, dy=0),
            dict(dx=2, la=-3, ra=-3, sway=-3),
            dict(dx=2, la=-2, ra=-2, sway=-3),
            dict(la=-1, ra=-1, sway=-2), dict(sway=-1), dict(), dict()][i]
    base = dict(base); base['rot'] = DEATH_ANG[i]
    return base

def pose_for(anim, d, i):
    if anim == 'idle':   return idle_pose(d, i)
    if anim == 'walk':   return locomotion(d, i, 6, False)
    if anim == 'run':    return locomotion(d, i, 6, True)
    if anim == 'attack': return attack_pose(d, i)
    if anim == 'dodge':  return dodge_pose(d, i)
    if anim == 'hurt':   return hurt_pose(d, i)
    if anim == 'death':  return death_pose(i)

# ------------------------------------------------------------------ POST
def flash(im):
    o = im.copy(); px = o.load()
    for y in range(FH):
        for x in range(FW):
            r, g, b, a = px[x, y]
            if a and (r, g, b) not in (W, HALO, FACE):
                px[x, y] = (int(r*0.5+176*0.5), int(g*0.5+164*0.5), int(b*0.5+208*0.5), 255)
    return o

_neutral = None
def fall(im, ang):
    global _neutral
    piv = (CX, BASE-2)
    if _neutral is None:
        cv = Cv(); draw_front(cv, {})
        rr = cv.im.rotate(-90, resample=Image.NEAREST, center=piv)
        x0, y0, x1, y1 = rr.getbbox()
        _neutral = (CX-(x0+x1)//2, 53-y1)
    e = (ang/90.0)**1.3
    return im.rotate(-ang, resample=Image.NEAREST, center=piv,
                     translate=(round(_neutral[0]*e), round(_neutral[1]*e)))

def outline(im):
    o = im.copy(); src = im.load(); dst = o.load()
    for y in range(FH):
        for x in range(FW):
            if src[x, y][3] == 0:
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xx, yy = x+dx, y+dy
                    if 0 <= xx < FW and 0 <= yy < FH and src[xx, yy][3]:
                        dst[x, y] = OUT+(255,); break
    return o

def render(anim, d, i):
    cv = Cv(); p = pose_for(anim, d, i)
    if 'ball' in p: draw_ball(cv, d, p['ball'], i)
    elif d == 'down': draw_front(cv, p)
    elif d == 'up': draw_front(cv, p, True)
    else: draw_side(cv, p)
    im = cv.im
    if p.get('flash'): im = flash(im)
    if anim == 'death': im = fall(im, p['rot'])
    if d == 'right':
        m = ImageOps.mirror(im); im = Image.new('RGBA', (FW, FH), (0,0,0,0)); im.paste(m, (1, 0))
    return outline(im)

# name, frames, fps, loop, per-frame duration multipliers
ANIMS = [('idle', 4, 5, True, None), ('walk', 6, 8, True, None), ('run', 6, 12, True, None),
         ('attack', 6, 14, False, [1.6, 1, 0.8, 0.8, 1.2, 1.6]),
         ('dodge', 6, 14, False, None), ('hurt', 3, 10, False, [1, 1.2, 1.2]),
         ('death', 8, 8, False, [1, 1, 1, 1, 1, 1.2, 1.5, 3])]

def build(outdir):
    rows = []
    for name, n, fps, loop, durs in ANIMS:
        for d in (['down'] if name == 'death' else DIRS):
            rows.append((name if name == 'death' else f'{name}_{d}', name, d, n, fps, loop, durs))
    sheet = Image.new('RGBA', (COLS*FW, len(rows)*FH), (0,0,0,0))
    meta = {'frame_size': [FW, FH], 'columns': COLS, 'rows': []}
    for r, (key, name, d, n, fps, loop, durs) in enumerate(rows):
        for i in range(n):
            sheet.paste(render(name, d, i), (i*FW, r*FH))
        meta['rows'].append(dict(name=key, row=r, frames=n, fps=fps, loop=loop))
    sheet.save(os.path.join(outdir, 'ashen_veil_player_spritesheet.png'))
    json.dump(meta, open(os.path.join(outdir, 'ashen_veil_player_spritesheet.json'), 'w'), indent=2)
    # Godot 4 SpriteFrames resource
    subs, anims = [], []
    for r, (key, name, d, n, fps, loop, durs) in enumerate(rows):
        fr = []
        for i in range(n):
            sid = f'AT_{r}_{i}'
            subs.append(f'[sub_resource type="AtlasTexture" id="{sid}"]\natlas = ExtResource("1_sheet")\nregion = Rect2({i*FW}, {r*FH}, {FW}, {FH})\n')
            fr.append('{\n"duration": %s,\n"texture": SubResource("%s")\n}' % ((durs[i] if durs else 1.0), sid))
        anims.append('{\n"frames": [%s],\n"loop": %s,\n"name": &"%s",\n"speed": %s\n}' %
                     (', '.join(fr), 'true' if loop else 'false', key, float(fps)))
    tres = ('[gd_resource type="SpriteFrames" load_steps=%d format=3]\n\n'
            '[ext_resource type="Texture2D" path="res://ashen_veil_player_spritesheet.png" id="1_sheet"]\n\n'
            % (len(subs)+2)) + '\n'.join(subs) + '\n[resource]\nanimations = [' + ', '.join(anims) + ']\n'
    open(os.path.join(outdir, 'ashen_veil_player_frames.tres'), 'w').write(tres)
    return sheet, rows

if __name__ == '__main__':
    build('/mnt/user-data/outputs')
