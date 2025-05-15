from OpenGL.GL   import *
from OpenGL.GLU  import *
from OpenGL.GLUT import *
import math, random, time


# ─────────────────────────────────────────────────────────────────────────────
# 1.  CONFIG – tweakables & constants
# ─────────────────────────────────────────────────────────────────────────────
# Window / camera
WIN_W, WIN_H        = 1000, 800
FOV_Y               = 60.0
CAM_DIST_DEFAULT    = 200.0
CAM_HEIGHT_DEFAULT  = 100.0

# World
TILE_SIZE           = 100
GROUND_HALF         = 1500

# Player
MOVE_SPEED          = 7.0
ROTATE_SPEED        = 4.0
PLAYER_HEIGHT       = 15.0
PLAYER_COLLIDE      = 15.0
WALL_MARGIN         = 10.0          # keep player this far from wall
INNER_MIN           = -GROUND_HALF + WALL_MARGIN
INNER_MAX           =  GROUND_HALF - WALL_MARGIN
HP_MAX              = 100.0
DMG_COOLDOWN_TIME   = 0.5

# Sword / attack animation
ATTACK_STEPS        = dict(slash1=15, pivot=8, slash2=15, ret=12)
ARC_Y, X_HI, X_LO   = 50.0, 45.0, -35.0
ATTACK_COOLDOWN     = 0.3
SWORD_RANGE         = 85.0
SWORD_ARC_DEG       = 35.0
SWORD_OFFSET_FWD    = 20.0

# Scoring
POINT_GHOST         = 50
POINT_BOSS          = POINT_GHOST * 2

# Ghosts
NUM_GHOSTS          = 50
GHOST_SIZE          = 40.0
GHOST_BASE_FLOAT_Y  = 75.0
GHOST_FLOAT_AMPL    = 7.0
GHOST_FLOAT_SPEED   = 0.025
GHOST_DETECTION_R   = 230.0
GHOST_CHASE_SPEED   = 0.65
GHOST_DEATH_TIME    = 1.5
GHOST_TOUCH_DPS     = 10.0
GHOST_BODY_CLR      = (0.92, 0.92, 0.98)
GHOST_FEATURE_CLR   = (0.10, 0.05, 0.05)
GHOST_TENTACLE_CLR  = (0.85, 0.85, 0.90)
GHOST_INVIS_DURATION= 5.0
FADE_TARGET_CLR     = (0.25, 0.25, 0.25)
FEATURE_FADE_MULT   = 1.5
NUM_TENTACLES       = 6
TENTACLE_LEN        = GHOST_SIZE * 1.3
TENTACLE_WID        = GHOST_SIZE * 0.08
TENTACLE_SWAY_ANG   = 15.0
TENTACLE_SWAY_SPEED = 0.5
TENTACLE_DRAG_STR   = 0.8
SPAWN_XZ_BOUNDS     = (-GROUND_HALF, GROUND_HALF)

# Boss
BOSS_SIZE           = GHOST_SIZE * 2
BOSS_MAX_HP         = 300.0
BOSS_TOUCH_DPS      = 20.0
BOSS_ATTACK_HIT     = 25.0
BOSS_DETECTION_R    = 500.0
BOSS_CHASE_SPEED    = 0.9
BOSS_FADE_TIME      = GHOST_DEATH_TIME * 1.5
BOSS_CORNERS        = [(-GROUND_HALF+80,  GROUND_HALF-80),
                       ( GROUND_HALF-80,  GROUND_HALF-80),
                       (-GROUND_HALF+80, -GROUND_HALF+80),
                       ( GROUND_HALF-80, -GROUND_HALF+80)]

# Eyeballs
NUM_EYEBALLS        = 60
EYEBALL_SIZE        = 20.0
EYEBALL_FLOAT_Y     = 35.0
EYEBALL_RESPAWN     = 10.0
EYEBALL_CLR         = (0.9, 0.9, 0.2)
EYEBALL_PUPIL_CLR   = (0.1, 0.1, 0.1)

# Wall visuals
WALL_THICKNESS      = 5.0
WALL_HEIGHT         = 40.0
WALL_COLOR          = (0.45, 0.25, 0.05)

# ─────────────────────────────────────────────────────────────────────────────
# 2.  GLOBAL STATE – runtime vars
# ─────────────────────────────────────────────────────────────────────────────
player_pos      = [0.0, PLAYER_HEIGHT, 0.0]
player_yaw      = 0.0
player_render_yaw = 0.0
cam_dist        = CAM_DIST_DEFAULT
cam_height      = CAM_HEIGHT_DEFAULT

is_attacking    = False
atk_phase       = 0
atk_step        = 0
arm_rot_x       = arm_rot_y = 0.0
atk_cooldown    = 0.0

player_hp       = HP_MAX
dmg_cooldown    = 0.0
ghost_visibility= GHOST_INVIS_DURATION
score           = 0

last_time       = 0.0

ghosts   = []
eyeballs = []
boss     = None

# ─────────────────────────────────────────────────────────────────────────────
# 3.  HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def lerp_color(c1, c2, f):
    return [c1[i] + (c2[i]-c1[i]) * f for i in range(3)]

def draw_text_2d(x, y, text, *, col=(1,1,1), font=GLUT_BITMAP_HELVETICA_18):
    r,g,b = col
    glColor3f(r,g,b)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text: glutBitmapCharacter(font, ord(ch))
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# ───── entity spawners ───────────────────────────────────────────────────────
def spawn_ghost(gid:int):
    gx = random.uniform(*SPAWN_XZ_BOUNDS)
    gz = random.uniform(*SPAWN_XZ_BOUNDS)
    phase = random.uniform(0, 2*math.pi)
    return {"id":gid,"pos":[gx,GHOST_BASE_FLOAT_Y,gz], "prev":[gx,0,gz],
            "vel":[0,0,0], "float_phase":phase,
            "tent_phase":[random.uniform(0,2*math.pi) for _ in range(NUM_TENTACLES)],
            "yaw":random.uniform(0,360), "state":"IDLE",
            "dying":False, "death_timer":0.0}

def spawn_boss():
    bx,bz = random.choice(BOSS_CORNERS)
    phase = random.uniform(0,2*math.pi)
    return {"pos":[bx,GHOST_BASE_FLOAT_Y,bz], "prev":[bx,0,bz], "vel":[0,0,0],
            "float_phase":phase, "yaw":random.uniform(0,360),
            "hp":BOSS_MAX_HP,"dying":False,"death_timer":BOSS_FADE_TIME}

# ─────────────────────────────────────────────────────────────────────────────
# 4.  INITIALISERS
# ─────────────────────────────────────────────────────────────────────────────
def init_ghosts():
    ghosts.clear()
    for i in range(NUM_GHOSTS):
        ghosts.append(spawn_ghost(i))

def init_eyeballs():
    eyeballs.clear()
    for i in range(NUM_EYEBALLS):
        ex = random.uniform(*SPAWN_XZ_BOUNDS)
        ez = random.uniform(*SPAWN_XZ_BOUNDS)
        eyeballs.append({"id":i,"pos":[ex,EYEBALL_FLOAT_Y,ez],
                         "active":True,"respawn":0.0})

# ─────────────────────────────────────────────────────────────────────────────
# 5.  RENDER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def draw_ground():
    for x in range(-GROUND_HALF, GROUND_HALF, TILE_SIZE):
        for z in range(-GROUND_HALF, GROUND_HALF, TILE_SIZE):
            glColor3f(0.2,0.2,0.2) if ((x//TILE_SIZE + z//TILE_SIZE) & 1)==0 else glColor3f(0.3,0.3,0.3)
            glBegin(GL_QUADS)
            glVertex3f(x,0,z); glVertex3f(x+TILE_SIZE,0,z)
            glVertex3f(x+TILE_SIZE,0,z+TILE_SIZE); glVertex3f(x,0,z+TILE_SIZE)
            glEnd()

def draw_walls():
    glColor3f(*WALL_COLOR)
    glBegin(GL_QUADS)
    # +Z
    glVertex3f(-GROUND_HALF,0, GROUND_HALF)
    glVertex3f( GROUND_HALF,0, GROUND_HALF)
    glVertex3f( GROUND_HALF,WALL_HEIGHT, GROUND_HALF+WALL_THICKNESS)
    glVertex3f(-GROUND_HALF,WALL_HEIGHT, GROUND_HALF+WALL_THICKNESS)
    # -Z
    glVertex3f( GROUND_HALF,0,-GROUND_HALF)
    glVertex3f(-GROUND_HALF,0,-GROUND_HALF)
    glVertex3f(-GROUND_HALF,WALL_HEIGHT,-GROUND_HALF-WALL_THICKNESS)
    glVertex3f( GROUND_HALF,WALL_HEIGHT,-GROUND_HALF-WALL_THICKNESS)
    # +X
    glVertex3f( GROUND_HALF,0, GROUND_HALF)
    glVertex3f( GROUND_HALF,0,-GROUND_HALF)
    glVertex3f( GROUND_HALF+WALL_THICKNESS,WALL_HEIGHT,-GROUND_HALF)
    glVertex3f( GROUND_HALF+WALL_THICKNESS,WALL_HEIGHT, GROUND_HALF)
    # -X
    glVertex3f(-GROUND_HALF,0,-GROUND_HALF)
    glVertex3f(-GROUND_HALF,0, GROUND_HALF)
    glVertex3f(-GROUND_HALF-WALL_THICKNESS,WALL_HEIGHT, GROUND_HALF)
    glVertex3f(-GROUND_HALF-WALL_THICKNESS,WALL_HEIGHT,-GROUND_HALF)
    glEnd()

# ---- player model -----------------------------------------------------------
def draw_player():
    glPushMatrix()
    glTranslatef(*player_pos)
    glRotatef(player_render_yaw,0,1,0)

    # legs
    glColor3f(0.3,0.3,0.8)
    for side in (-1,1):
        glPushMatrix()
        glTranslatef(side*10,10,0)
        glScalef(0.25,1.2,0.25)
        glutSolidCube(30)
        glPopMatrix()

    # torso
    glColor3f(0.8,0.3,0.3)
    glPushMatrix(); 
    glTranslatef(0,30,0)
    glScalef(1,1.8,0.5)
    glutSolidCube(30)
    glPopMatrix()

    # head
    glColor3f(1,0.8,0.6)
    glPushMatrix(); glTranslatef(0,30+27+10,0); glutSolidSphere(12,15,15); glPopMatrix()


    # static left arm
    glColor3f(1,0.7,0.5)
    glPushMatrix()
    glTranslatef(-20,45,10)
    glRotatef(-70,1,0,0)
    glRotatef(20,0,0,1)
    glScalef(0.25,1.1,0.25)
    glutSolidCube(30)
    glPopMatrix()

    # animated right arm + sword
    glPushMatrix()
    glTranslatef(20,45,10)
    glRotatef(arm_rot_y,0,1,0)
    glRotatef(-70,1,0,0)
    glRotatef(-20,0,0,1)
    glRotatef(arm_rot_x,1,0,0)

    # upper arm
    glColor3f(1,0.7,0.5)
    glPushMatrix()
    glScalef(0.25,1.1,0.25)
    glutSolidCube(30)
    glPopMatrix()

    # sword
    glPushMatrix()
    glTranslatef(0, 15*1.1, 0)
    glRotatef(-90,1,0,0)
    glRotatef(45,0,0,1)

    glColor3f(0.4,0.2,0.1)      # hilt
    glPushMatrix(); glTranslatef(0,0,6); glScalef(2.2,2.2,12); glutSolidCube(1); glPopMatrix()
    glColor3f(0.5,0.5,0.55)     # guard
    glPushMatrix(); glTranslatef(0,0,13); glScalef(10,1.5,2.5); glutSolidCube(1); glPopMatrix()
    glColor3f(0.75,0.75,0.8)    # blade
    glPushMatrix(); glTranslatef(0,0,13+2.5+22.5); glScalef(5,0.8,45); glutSolidCube(1); glPopMatrix()

    glPopMatrix()  # sword
    glPopMatrix()  # animated arm
    glPopMatrix()  # whole player

# ---- eyeballs ---------------------------------------------------------------
def draw_eyeballs():
    for eb in eyeballs:
        if not eb["active"]: continue
        glPushMatrix()
        glTranslatef(*eb["pos"])
        glColor3f(*EYEBALL_CLR); glutSolidSphere(EYEBALL_SIZE,16,16)
        glColor3f(*EYEBALL_PUPIL_CLR)
        glPushMatrix(); glTranslatef(0,0,EYEBALL_SIZE*0.8)
        glutSolidSphere(EYEBALL_SIZE*0.3,10,10); glPopMatrix()
        glPopMatrix()

# ---- ghosts -----------------------------------------------------------------
def draw_single_ghost(g, vis_global):
    vis = vis_global if not g["dying"] else max(0.0, g["death_timer"]/(GHOST_DEATH_TIME*0.85))
    if vis<=0.01 and not g["dying"]: return
    scale = vis if g["dying"] else 1.0
    body_c = (0.05,0.05,0.05) if g["dying"] else lerp_color(GHOST_BODY_CLR, FADE_TARGET_CLR, 1-vis)
    feat_c = (0,0,0)           if g["dying"] else lerp_color(GHOST_FEATURE_CLR, body_c, (1-vis)*FEATURE_FADE_MULT)
    tent_c = body_c if g["dying"] else lerp_color(GHOST_TENTACLE_CLR, FADE_TARGET_CLR, 1-vis)

    glPushMatrix()
    glTranslatef(*g["pos"]); glScalef(scale,scale,scale); glRotatef(g["yaw"],0,1,0)

    glColor3f(*body_c); glutSolidCube(GHOST_SIZE)

    if vis>0.05 and not g["dying"]:
        face_off = GHOST_SIZE*0.5+0.1
        eye_sep  = GHOST_SIZE*0.15
        eye_w    = GHOST_SIZE*0.18*math.sqrt(vis)
        eye_h    = GHOST_SIZE*0.22*math.sqrt(vis)
        mouth_w  = GHOST_SIZE*0.3*math.sqrt(vis)
        mouth_h  = GHOST_SIZE*0.1*math.sqrt(vis)
        glColor3f(*feat_c)
        for s in (-1,1):
            glPushMatrix(); glTranslatef(s*eye_sep,GHOST_SIZE*0.15,face_off)
            glScalef(eye_w,eye_h,0.1); glutSolidCube(1); glPopMatrix()
        glPushMatrix(); glTranslatef(0,-GHOST_SIZE*0.2,face_off)
        glScalef(mouth_w,mouth_h,0.1); glutSolidCube(1); glPopMatrix()

    # tentacles
    if not g["dying"] or g["death_timer"]>GHOST_DEATH_TIME*0.1:
        vx,_,vz = g["vel"]; speed = math.hypot(vx,vz)
        drag_x  = min(75, speed*150*TENTACLE_DRAG_STR)
        drag_yaw= math.degrees(math.atan2(-vx,-vz))-g["yaw"] if speed>0.01 else 0
        glColor3f(*tent_c)
        for i in range(NUM_TENTACLES):
            sway = g["tent_phase"][i] + g["float_phase"]*TENTACLE_SWAY_SPEED
            sway_x = math.sin(sway)*TENTACLE_SWAY_ANG
            sway_z = math.cos(sway*0.7)*TENTACLE_SWAY_ANG*0.5
            off_x  = (i-(NUM_TENTACLES-1)/2)*(GHOST_SIZE*0.7/max(1,NUM_TENTACLES-1))
            glPushMatrix()
            glTranslatef(off_x,-GHOST_SIZE*0.5,0)
            glRotatef(drag_yaw,0,1,0); glRotatef(drag_x,1,0,0)
            glRotatef(sway_x,1,0,0); glRotatef(sway_z,0,0,1)
            glPushMatrix()
            glTranslatef(0,-TENTACLE_LEN/2,0)
            glScalef(TENTACLE_WID,TENTACLE_LEN,TENTACLE_WID); glutSolidCube(1)
            glPopMatrix(); glPopMatrix()
    glPopMatrix()

def draw_all_ghosts():
    vis_global = max(0.0, ghost_visibility / GHOST_INVIS_DURATION)
    for g in ghosts:
        if g["dying"] and g["death_timer"]<=0: continue
        vis = vis_global if not g["dying"] else None
        draw_single_ghost(g, vis)

# ---- boss -------------------------------------------------------------------
def draw_boss():
    if not boss or (boss["dying"] and boss["death_timer"]<=0): return
    vis = 1.0 if not boss["dying"] else max(0.0,boss["death_timer"]/BOSS_FADE_TIME)
    body_c = lerp_color(GHOST_BODY_CLR, FADE_TARGET_CLR, 1-vis)
    feat_c = lerp_color(GHOST_FEATURE_CLR, body_c, (1-vis)*FEATURE_FADE_MULT)
    glPushMatrix()
    glTranslatef(*boss["pos"]); glRotatef(boss["yaw"],0,1,0)
    glScalef(BOSS_SIZE/GHOST_SIZE, BOSS_SIZE/GHOST_SIZE, BOSS_SIZE/GHOST_SIZE)

    glColor3f(*body_c); glutSolidCube(GHOST_SIZE)
    if vis>0.05 and not boss["dying"]:
        face_off = GHOST_SIZE*0.5+0.1
        eye_sep  = GHOST_SIZE*0.15
        eye_w    = GHOST_SIZE*0.18*math.sqrt(vis)
        eye_h    = GHOST_SIZE*0.22*math.sqrt(vis)
        mouth_w  = GHOST_SIZE*0.3*math.sqrt(vis)
        mouth_h  = GHOST_SIZE*0.1*math.sqrt(vis)
        glColor3f(*feat_c)
        for s in (-1,1):
            glPushMatrix(); glTranslatef(s*eye_sep,GHOST_SIZE*0.15,face_off)
            glScalef(eye_w,eye_h,0.1); glutSolidCube(1); glPopMatrix()
        glPushMatrix(); glTranslatef(0,-GHOST_SIZE*0.2,face_off)
        glScalef(mouth_w,mouth_h,0.1); glutSolidCube(1); glPopMatrix()
    glPopMatrix()

# ─────────────────────────────────────────────────────────────────────────────
# 6.  INPUT HANDLERS
# ─────────────────────────────────────────────────────────────────────────────
def key_down(key, *_):
    global player_pos, player_yaw
    key = key.lower()

    sin_y, cos_y = math.sin(math.radians(player_yaw)), math.cos(math.radians(player_yaw))
    fwd  = ( sin_y*MOVE_SPEED, cos_y*MOVE_SPEED)
    strf = (-cos_y*MOVE_SPEED, sin_y*MOVE_SPEED)

    if key==b'w': player_pos[0]+=fwd[0];  player_pos[2]+=fwd[1]
    if key==b's': player_pos[0]-=fwd[0];  player_pos[2]-=fwd[1]
    if key==b'e': player_pos[0]+=strf[0]; player_pos[2]+=strf[1]
    if key==b'q': player_pos[0]-=strf[0]; player_pos[2]-=strf[1]
    if key==b'a': player_yaw+=ROTATE_SPEED
    if key==b'd': player_yaw-=ROTATE_SPEED
    player_yaw%=360
    
    # clamp inside wall
    player_pos[0]=max(INNER_MIN,min(INNER_MAX,player_pos[0]))
    player_pos[2]=max(INNER_MIN,min(INNER_MAX,player_pos[2]))

def special_key(key,*_):
    global cam_height, cam_dist
    if key==GLUT_KEY_UP:        cam_height+=5
    if key==GLUT_KEY_DOWN:      cam_height=max(5,cam_height-5)
    if key==GLUT_KEY_PAGE_UP:   cam_dist  =max(50,cam_dist-10)
    if key==GLUT_KEY_PAGE_DOWN: cam_dist+=10

def mouse_click(btn,state,*_):
    global is_attacking, atk_phase, atk_step, arm_rot_x, arm_rot_y, atk_cooldown
    if btn==GLUT_LEFT_BUTTON and state==GLUT_DOWN and not is_attacking and player_hp>0 and atk_cooldown<=0:
        is_attacking=True
        atk_phase=1
        atk_step=0
        arm_rot_x=arm_rot_y=0
        atk_cooldown=ATTACK_COOLDOWN

# ─────────────────────────────────────────────────────────────────────────────
# 7.  CAMERA
# ─────────────────────────────────────────────────────────────────────────────
def setup_camera():
    global player_render_yaw

    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(FOV_Y, WIN_W/WIN_H, 0.1, 3000.0)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()

    rad=math.radians(player_yaw)
    cx=player_pos[0]-math.sin(rad)*cam_dist
    cz=player_pos[2]-math.cos(rad)*cam_dist
    cy=player_pos[1]+cam_height
    gluLookAt(cx,cy,cz, player_pos[0],player_pos[1]+30,player_pos[2], 0,1,0)

    dx,dz = cx-player_pos[0], cz-player_pos[2]
    player_render_yaw=math.degrees(math.atan2(dx,dz)) if (dx or dz) else player_yaw

# ─────────────────────────────────────────────────────────────────────────────
# 8.  UPDATE – main game loop logic
# ─────────────────────────────────────────────────────────────────────────────
def update():
    global last_time, atk_cooldown, dmg_cooldown, ghost_visibility
    global is_attacking, atk_phase, atk_step, arm_rot_x, arm_rot_y
    global player_hp, score, boss

    # --- delta-time ----------------------------------------------------------
    # now=glutGet(GLUT_ELAPSED_TIME)/1000.0
    now = time.perf_counter()
    dt=min(max(now-last_time,1/60),0.1)
    last_time=now

    # --- cool-downs ----------------------------------------------------------
    atk_cooldown=max(0, atk_cooldown-dt)
    dmg_cooldown=max(0, dmg_cooldown-dt)
    ghost_visibility=max(0, ghost_visibility-dt)

    # --- eyeball pick-ups ----------------------------------------------------
    for eb in eyeballs:
        if eb["active"]:
            d2=((player_pos[0]-eb["pos"][0])**2 +
                (player_pos[1]+30-eb["pos"][1])**2 +
                (player_pos[2]-eb["pos"][2])**2)
            if d2<(PLAYER_COLLIDE+EYEBALL_SIZE)**2:
                eb["active"]=False; eb["respawn"]=EYEBALL_RESPAWN
                ghost_visibility+=GHOST_INVIS_DURATION
        else:
            if eb["respawn"]>0:
                eb["respawn"]-=dt
                if eb["respawn"]<=0:
                    eb["pos"][0]=random.uniform(*SPAWN_XZ_BOUNDS)
                    eb["pos"][2]=random.uniform(*SPAWN_XZ_BOUNDS)
                    eb["active"]=True

    # --- attack animation & sword hits --------------------------------------
    if is_attacking and player_hp>0:
        atk_step+=1
        def prog(steps): return min(1.0, atk_step/steps)
        ease=lambda p: math.sin(p*math.pi/2)

        if atk_phase==1:
            p=prog(ATTACK_STEPS["slash1"])
            arm_rot_y= ARC_Y-2*ARC_Y*ease(p)
            arm_rot_x= X_HI + (X_LO-X_HI)*ease(p)
            if atk_step>=ATTACK_STEPS["slash1"]: atk_phase,atk_step=2,0
        elif atk_phase==2:
            p=prog(ATTACK_STEPS["pivot"])
            arm_rot_y=-ARC_Y
            arm_rot_x= X_LO+(X_HI-X_LO)*ease(p)
            if atk_step>=ATTACK_STEPS["pivot"]:  atk_phase,atk_step=3,0
        elif atk_phase==3:
            p=prog(ATTACK_STEPS["slash2"])
            arm_rot_y=-ARC_Y+2*ARC_Y*ease(p)
            arm_rot_x= X_HI + (X_LO-X_HI)*ease(p)
            if atk_step>=ATTACK_STEPS["slash2"]: atk_phase,atk_step=4,0
        elif atk_phase==4:
            p=prog(ATTACK_STEPS["ret"])
            arm_rot_y= ARC_Y*math.cos(p*math.pi/2)
            arm_rot_x= X_LO*math.cos(p*math.pi/2)
            if atk_step>=ATTACK_STEPS["ret"]:
                is_attacking=False; atk_phase=atk_step=0; arm_rot_x=arm_rot_y=0

        dmg_window=((atk_phase==1 and ATTACK_STEPS["slash1"]*0.2<atk_step<ATTACK_STEPS["slash1"]*0.85) or
                    (atk_phase==3 and ATTACK_STEPS["slash2"]*0.2<atk_step<ATTACK_STEPS["slash2"]*0.85))
        if dmg_window:
            rad=math.radians(player_render_yaw+180)
            ax=player_pos[0]+math.sin(rad)*SWORD_OFFSET_FWD
            ay=player_pos[1]+40
            az=player_pos[2]+math.cos(rad)*SWORD_OFFSET_FWD

            # normal ghosts
            for g in ghosts:
                if g["dying"]: continue
                dx,dy,dz=g["pos"][0]-ax,g["pos"][1]-ay,g["pos"][2]-az
                if dx*dx+dy*dy+dz*dz<SWORD_RANGE**2:
                    dist_xz=math.hypot(dx,dz) or 0.001
                    dot=(dx*math.sin(rad)+dz*math.cos(rad))/dist_xz
                    if math.degrees(math.acos(max(-1,min(1,dot))))<SWORD_ARC_DEG:
                        g["dying"]=True; g["death_timer"]=GHOST_DEATH_TIME
                        score+=POINT_GHOST

            # boss
            if boss and not boss["dying"]:
                dx=boss["pos"][0]-ax; dy=boss["pos"][1]-ay; dz=boss["pos"][2]-az
                if dx*dx+dy*dy+dz*dz<(SWORD_RANGE*1.5)**2:
                    dist_xz=math.hypot(dx,dz) or 0.001
                    dot=(dx*math.sin(rad)+dz*math.cos(rad))/dist_xz
                    if math.degrees(math.acos(max(-1,min(1,dot))))<SWORD_ARC_DEG:
                        boss["hp"]-=BOSS_ATTACK_HIT
                        if boss["hp"]<=0:
                            boss["dying"]=True; boss["death_timer"]=BOSS_FADE_TIME
                            score+=POINT_BOSS

    # cancel attack if player dead
    if player_hp<=0 and is_attacking:
        is_attacking=False; atk_phase=atk_step=0; arm_rot_x=arm_rot_y=0

    # --- ghost AI loop -------------------------------------------------------
    survivors=[]
    for g in ghosts:
        if g["dying"]:
            g["death_timer"]-=dt
            if g["death_timer"]>0: survivors.append(g)
            else: survivors.append(spawn_ghost(g["id"]))
            continue

        g["prev"][:]=g["pos"][:]
        g["float_phase"]=(g["float_phase"]+GHOST_FLOAT_SPEED*dt*60)%(2*math.pi)
        g["pos"][1]=GHOST_BASE_FLOAT_Y+math.sin(g["float_phase"])*GHOST_FLOAT_AMPL

        dx,dz=player_pos[0]-g["pos"][0], player_pos[2]-g["pos"][2]
        dist=math.hypot(dx,dz) or 0.001
        tgt_yaw=math.degrees(math.atan2(dx,dz))
        g["yaw"]=(g["yaw"]+(((tgt_yaw-g["yaw"]+180)%360)-180)*0.05*dt*60)%360

        if dist<GHOST_DETECTION_R and player_hp>0:
            if dist>PLAYER_COLLIDE:
                g["pos"][0]+=dx/dist*GHOST_CHASE_SPEED*dt*60
                g["pos"][2]+=dz/dist*GHOST_CHASE_SPEED*dt*60
        for i in range(3): g["vel"][i]=g["pos"][i]-g["prev"][i]

        if dmg_cooldown<=0 and player_hp>0:
            dy=(player_pos[1]+30)-g["pos"][1]
            if dx*dx+dy*dy+dz*dz<(PLAYER_COLLIDE+GHOST_SIZE/2)**2:
                player_hp=max(0,player_hp-GHOST_TOUCH_DPS)
                dmg_cooldown=DMG_COOLDOWN_TIME
        survivors.append(g)
    ghosts[:] = survivors

    # --- boss update ---------------------------------------------------------
    if boss:
        if boss["dying"]: boss["death_timer"]-=dt
        else:
            boss["prev"][:]=boss["pos"][:]
            boss["float_phase"]=(boss["float_phase"]+GHOST_FLOAT_SPEED*dt*60)%(2*math.pi)
            boss["pos"][1]=GHOST_BASE_FLOAT_Y+math.sin(boss["float_phase"])*GHOST_FLOAT_AMPL
            dx,dz=player_pos[0]-boss["pos"][0], player_pos[2]-boss["pos"][2]
            dist=math.hypot(dx,dz) or 0.001
            tgt_yaw=math.degrees(math.atan2(dx,dz))
            boss["yaw"]=(boss["yaw"]+(((tgt_yaw-boss["yaw"]+180)%360)-180)*0.05*dt*60)%360
            if dist<BOSS_DETECTION_R and player_hp>0 and dist>PLAYER_COLLIDE:
                boss["pos"][0]+=dx/dist*BOSS_CHASE_SPEED*dt*60
                boss["pos"][2]+=dz/dist*BOSS_CHASE_SPEED*dt*60
            if dmg_cooldown<=0 and player_hp>0:
                dy=(player_pos[1]+30)-boss["pos"][1]
                if dx*dx+dy*dy+dz*dz<(PLAYER_COLLIDE+BOSS_SIZE/2)**2:
                    player_hp=max(0,player_hp-BOSS_TOUCH_DPS*dt)
                    dmg_cooldown=DMG_COOLDOWN_TIME

    # --- auto-respawn boss when gone -----------------------------------------
    if boss is None or (boss["dying"] and boss["death_timer"]<=0):
        boss=spawn_boss()

    glutPostRedisplay()

# ─────────────────────────────────────────────────────────────────────────────
# 9.  DISPLAY
# ─────────────────────────────────────────────────────────────────────────────
def show_screen():
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    setup_camera()

    draw_ground(); draw_walls()
    draw_eyeballs(); draw_all_ghosts(); draw_boss()
    if player_hp>0: draw_player()

    # HUD
    draw_text_2d(10,WIN_H-30, f"HP   : {int(player_hp)}/{int(HP_MAX)}", col=(0.1,1,0.1))
    draw_text_2d(10,WIN_H-60, f"Score: {score}",                       col=(1,1,0.2))
    # draw_text_2d(10,WIN_H-90, f"Yaw  : {player_yaw:.1f}")
    draw_text_2d(10, WIN_H-130,f"Ghost Visible : {ghost_visibility:.1f}s", col=(0.8,0.8,1))

    if player_hp<=0:
        draw_text_2d(WIN_W//2-80,WIN_H//2,"GAME OVER",col=(1,0,0),
                     font=GLUT_BITMAP_TIMES_ROMAN_24)

    glutSwapBuffers()

# ─────────────────────────────────────────────────────────────────────────────
# 10.  MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    global last_time, boss
    glutInit(); glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
    glutInitWindowSize(WIN_W,WIN_H); glutCreateWindow(b"Ghost Of OpenGL")

    last_time= time.perf_counter()
    init_ghosts(); init_eyeballs(); boss=spawn_boss()

    glutDisplayFunc(show_screen)
    glutKeyboardFunc(key_down)
    glutSpecialFunc(special_key)
    glutMouseFunc(mouse_click)
    glutIdleFunc(update)

    print("""
Controls
--------
W/S          Move forward / backward
Q/E          Strafe left / right
A/D          Rotate left / right
Mouse Left   X-style sword slash
Arrow Up/Down, PgUp/PgDn  Camera height / distance
""")
    glutMainLoop()

if __name__=="__main__":
    main()
