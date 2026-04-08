from tools import *
from objects import *
from routines import *

import math


# ============================================================
# Helpers de desenho (render) - compatível mesmo sem "circle"
# ============================================================

def _safe_line(agent, a, b, color=(255, 255, 255)):
    try:
        agent.line(a, b, color)
        return True
    except Exception:
        return False


def _draw_circle(agent, center, radius=250, color=(255, 255, 255), steps=24, z_override=None):
    pts = []
    z = center.z if z_override is None else z_override
    for i in range(steps + 1):
        t = (i / steps) * (math.pi * 2)
        pts.append(Vector3(center.x + math.cos(t) * radius, center.y + math.sin(t) * radius, z))

    for i in range(len(pts) - 1):
        _safe_line(agent, pts[i], pts[i + 1], color)


def _draw_arrow(agent, start, end, color=(255, 255, 255), head_len=180, head_angle_deg=28):
    _safe_line(agent, start, end, color)

    dir_vec = (end - start)
    if dir_vec.magnitude() < 1:
        return
    d = dir_vec.normalize()

    ang = math.radians(head_angle_deg)
    left = Vector3(
        d.x * math.cos(ang) - d.y * math.sin(ang),
        d.x * math.sin(ang) + d.y * math.cos(ang),
        0
    )
    right = Vector3(
        d.x * math.cos(-ang) - d.y * math.sin(-ang),
        d.x * math.sin(-ang) + d.y * math.cos(-ang),
        0
    )

    p1 = end - left.normalize() * head_len
    p2 = end - right.normalize() * head_len
    _safe_line(agent, end, p1, color)
    _safe_line(agent, end, p2, color)


def _draw_text_3d(agent, location, text, color=(255, 255, 255)):
    for attr in ["draw_string_3d", "string", "text", "draw_text_3d"]:
        fn = getattr(agent, attr, None)
        if callable(fn):
            try:
                fn(location, text, color)
                return True
            except Exception:
                pass

    renderer = getattr(agent, "renderer", None)
    if renderer is not None:
        for attr in ["draw_string_3d", "draw_string_2d", "draw_string"]:
            fn = getattr(renderer, attr, None)
            if callable(fn):
                try:
                    try:
                        fn(location, 1, 1, text, color)
                        return True
                    except Exception:
                        try:
                            fn(location.x, location.y, location.z, 1, 1, text, color)
                            return True
                        except Exception:
                            pass
                except Exception:
                    pass

    return False


# ============================================================
# Helpers de "previsão" simples da bola (para render e timing)
# ============================================================

GRAVITY_Z = -650.0  # Rocket League approx

def _ballistic_ball_pos(ball_loc, ball_vel, dt):
    return Vector3(
        ball_loc.x + ball_vel.x * dt,
        ball_loc.y + ball_vel.y * dt,
        ball_loc.z + ball_vel.z * dt + 0.5 * GRAVITY_Z * dt * dt
    )


def _ballistic_ball_vel(ball_vel, dt):
    return Vector3(ball_vel.x, ball_vel.y, ball_vel.z + GRAVITY_Z * dt)


def _sample_ball_path(ball_loc, ball_vel, t_end, step=0.10):
    pts = []
    t = 0.0
    loc = ball_loc
    vel = ball_vel
    while t < t_end:
        pts.append(loc)
        loc = _ballistic_ball_pos(loc, vel, step)
        vel = _ballistic_ball_vel(vel, step)

        if loc.z < 0:
            loc = Vector3(loc.x, loc.y, 0)
            vel = Vector3(vel.x, vel.y, 0)

        t += step
    pts.append(loc)
    return pts


# ============================================================
# Helpers de estratégia / matemática
# ============================================================

def _cap(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _eta_to_point(agent, car, point):
    to = point - car.location
    dist = to.magnitude()
    if dist < 1:
        return 0.0

    local = car.local(to)
    angle = abs(math.atan2(local.x, local.y))  # 0 -> alinhado, pi -> de costas

    speed = max(300.0, car.velocity.magnitude())
    base = dist / speed

    turn_penalty = (angle / math.pi) * 1.2
    slow_penalty = 0.3 if speed < 900 else 0.0

    return base + turn_penalty + slow_penalty


def _role_and_ranks(agent):
    """
    Retorna:
      - my_role: "FIRST" / "SECOND" / "THIRD"
      - i_am_last_man: bool (mais perto do nosso gol)
      - etas_sorted
      - goal_sorted
      - have_mates: bool (tem teammate além de mim)
    """
    # garante que friends não inclui "me"
    raw_friends = list(getattr(agent, "friends", []))
    friends = [f for f in raw_friends if getattr(f, "index", None) != agent.me.index]
    have_mates = len(friends) > 0

    players = [agent.me] + friends
    ball_loc = agent.ball.location
    own_goal = agent.friend_goal.location

    etas = []
    goal_dists = []

    for p in players:
        etas.append((p.index, _eta_to_point(agent, p, ball_loc)))
        goal_dists.append((p.index, (p.location - own_goal).magnitude()))

    etas_sorted = sorted(etas, key=lambda x: x[1])
    goal_sorted = sorted(goal_dists, key=lambda x: x[1])

    my_idx = agent.me.index
    my_rank_eta = [i for i, (idx, _) in enumerate(etas_sorted) if idx == my_idx][0]
    my_rank_goal = [i for i, (idx, _) in enumerate(goal_sorted) if idx == my_idx][0]

    i_am_last_man = (my_rank_goal == 0)

    # Ajuste específico (pra 1v1 e evitar "chuta -> recua gol -> chuta -> recua"):
    # sem mates, você precisa ser FIRST (pressão) e só recuar quando threat alto.
    if not have_mates:
        my_role = "FIRST"
        return my_role, i_am_last_man, etas_sorted, goal_sorted, have_mates

    if my_rank_eta == 0 and not i_am_last_man:
        my_role = "FIRST"
    elif i_am_last_man:
        my_role = "THIRD"
    else:
        my_role = "SECOND"

    return my_role, i_am_last_man, etas_sorted, goal_sorted, have_mates


def _threat_level(agent):
    s = side(agent.team)

    ball = agent.ball
    me = agent.me
    own_goal = agent.friend_goal.location

    ball_on_our_side = (ball.location.y * s) < 0
    ball_towards_our_goal = (ball.velocity.y * s) < -200
    ball_close_to_goal = (ball.location - own_goal).magnitude() < 2800

    foe_best_eta = 999
    for f in getattr(agent, "foes", []):
        foe_best_eta = min(foe_best_eta, _eta_to_point(agent, f, ball.location))
    my_eta = _eta_to_point(agent, me, ball.location)

    foe_beats_me = foe_best_eta + 0.10 < my_eta

    threat = 0.0
    if ball_on_our_side: threat += 0.35
    if ball_towards_our_goal: threat += 0.35
    if ball_close_to_goal: threat += 0.35
    if foe_beats_me: threat += 0.35

    return _cap(threat, 0.0, 1.5)


def _desired_approach_speed(agent, dist_to_ball, intercept_z, ball_vz):
    if dist_to_ball > 2200:
        base = 2300
    elif dist_to_ball > 1400:
        base = 2000
    elif dist_to_ball > 800:
        base = 1600
    else:
        base = 1100

    if intercept_z > 160:
        base -= 400
    if ball_vz < -200 and intercept_z > 120:
        base -= 300

    return _cap(base, 600, 2300)


def _choose_shot_target(agent, shot_kind):
    if shot_kind == "goal":
        return agent.foe_goal.location
    if shot_kind == "clear":
        s = side(agent.team)
        x = 3800 if agent.ball.location.x < 0 else -3800
        y = 1800 * s
        return Vector3(x, y, 0)
    if shot_kind == "wallshot":
        return agent.foe_goal.location
    return agent.foe_goal.location


def _shot_score(agent, shot, shot_kind="goal"):
    me = agent.me
    now = agent.time

    intercept_time = getattr(shot, "intercept_time", None)
    ball_loc = getattr(shot, "ball_location", None)

    if intercept_time is None or ball_loc is None:
        return -999999

    dt = max(0.01, intercept_time - now)
    dist = (ball_loc - me.location).magnitude()
    avg_speed = dist / dt

    to_ball = (ball_loc - me.location)
    to_ball_n = to_ball.normalize() if to_ball.magnitude() > 1 else Vector3(0, 1, 0)

    target_point = _choose_shot_target(agent, shot_kind)
    ball_to_target = (target_point - ball_loc)
    ball_to_target_n = ball_to_target.normalize() if ball_to_target.magnitude() > 1 else Vector3(0, 1, 0)

    local = me.local(to_ball)
    facing = _cap(local.y / (to_ball.magnitude() + 1e-6), -1, 1)
    align = _cap(to_ball_n.dot(ball_to_target_n), -1, 1)

    ratio = getattr(shot, "ratio", 1.0)

    height_penalty = 0.0
    if ball_loc.z > 220 and me.boost < 40:
        height_penalty += 0.7
    if ball_loc.z > 380 and me.boost < 60:
        height_penalty += 1.2

    threat = _threat_level(agent)
    risk_penalty = 0.0
    if threat > 0.9 and shot_kind == "goal":
        risk_penalty += 0.6

    score = (avg_speed * 0.55) + (ratio * 900) + (align * 500) + (facing * 300)
    score -= (height_penalty * 900)
    score -= (risk_penalty * 800)

    return score


def _pick_best_shot(agent, shots_dict):
    best = None
    best_kind = None
    best_score = -999999

    for kind in ["goal", "clear"]:
        for shot in shots_dict.get(kind, []):
            sc = _shot_score(agent, shot, kind)
            if sc > best_score:
                best = shot
                best_score = sc
                best_kind = kind

    return best, best_kind, best_score


def _shot_is_aerial(shot):
    name = shot.__class__.__name__.lower()
    return ("aerial" in name) or ("air" in name)


def _shot_is_wall(shot):
    name = shot.__class__.__name__.lower()
    return ("wall" in name)


def _has_routine(name):
    return name in globals() and callable(globals()[name])


# ============================================================
# Aerial inteligente: escolher intercepto futuro com tempo de preparo
# ============================================================

def _aerial_required_time(agent, intercept_loc):
    """
    Estima um tempo mínimo pra conseguir chegar num intercepto aéreo.
    (sem mudar sua base, só garantindo que o aerial não é "cedo demais")
    """
    me = agent.me
    to = intercept_loc - me.location
    dist = to.magnitude()

    # penaliza giro (se alvo muito de lado/atrás)
    local = me.local(to)
    angle = abs(math.atan2(local.x, max(1e-6, local.y)))  # 0 alinhado
    turn_pen = (angle / math.pi) * 0.55

    # penaliza altura
    z = max(0.0, intercept_loc.z - me.location.z)
    height_pen = _cap(z / 900.0, 0.0, 1.0) * 0.75

    # base por distância (aerial precisa de "tempo de spool")
    base = dist / 1550.0  # ~ velocidade efetiva média no ar (aprox)
    base = _cap(base, 0.55, 2.6)

    # se boost baixo, exige mais tempo
    boost = me.boost
    boost_pen = 0.35 if boost < 40 else 0.15 if boost < 60 else 0.0

    return base + turn_pen + height_pen + boost_pen


def _pick_best_aerial_shot(agent, shots_dict):
    """
    Escolhe um aerial que dê tempo real de chegar.
    Procura tanto em "goal" quanto "clear".
    """
    now = agent.time
    best = None
    best_kind = None
    best_score = -999999

    for kind in ["goal", "clear"]:
        for shot in shots_dict.get(kind, []):
            intercept_time = getattr(shot, "intercept_time", None)
            intercept_loc = getattr(shot, "ball_location", None)
            if intercept_time is None or intercept_loc is None:
                continue

            dt = intercept_time - now
            if dt < 0.1:
                continue

            # só trata como aerial se for realmente alto ou class indicar
            if not (_shot_is_aerial(shot) or intercept_loc.z > 250):
                continue

            req = _aerial_required_time(agent, intercept_loc)
            if dt < req:
                continue

            sc = _shot_score(agent, shot, kind) + (dt * 40.0)  # leve bias pra "mais tempo" quando tudo igual
            if sc > best_score:
                best = shot
                best_kind = kind
                best_score = sc

    return best, best_kind, best_score


# ============================================================
# Wallshot: usar rotina do GoslingUtils se existir + render
# ============================================================

def _ball_near_wall(agent):
    b = agent.ball.location
    return (abs(b.x) > 3600) or (abs(b.y) > 4950)


def _try_push_wallshot(agent):
    """
    Tenta acionar wallshot usando rotinas do GoslingUtils, sem quebrar se não existir.
    Retorna True se conseguiu pushar algo.
    """
    if not (_has_routine("wall_shot") or _has_routine("wallshot") or _has_routine("wallShot")):
        return False

    target = agent.foe_goal.location

    for nm in ["wall_shot", "wallshot", "wallShot"]:
        fn = globals().get(nm, None)
        if callable(fn):
            try:
                # tentativas de assinatura comuns
                try:
                    agent.push(fn(target))
                    return True
                except Exception:
                    try:
                        agent.push(fn(agent.foe_goal.left_post, agent.foe_goal.right_post))
                        return True
                    except Exception:
                        try:
                            agent.push(fn())
                            return True
                        except Exception:
                            pass
            except Exception:
                pass

    return False


# ============================================================
# Kickoff: não termina ao tocar na bola; termina quando kickoff_flag acabar
# ============================================================

class KickoffWrapper:
    """
    Mantém a lógica de kickoff rodando enquanto kickoff_flag estiver True.
    Se a rotina kickoff() "acabar cedo" (ex: ao tocar a bola), a wrapper continua (recria) até o kickoff acabar.
    """
    def __init__(self):
        self.inner = kickoff() if _has_routine("kickoff") else None

    def run(self, agent):
        if not agent.kickoff_flag:
            return True  # pop quando o kickoff acabar

        if self.inner is None:
            # fallback simples: acelerar pra bola
            to_ball = agent.ball.location - agent.me.location
            local = agent.me.local(to_ball)
            defaultPD(agent, local)
            defaultThrottle(agent, 2300)
            agent.controller.boost = True
            return False

        done = False
        try:
            done = bool(self.inner.run(agent))
        except Exception:
            done = False

        # Se o kickoff() encerrou cedo (ex: tocou na bola), recria e continua até kickoff_flag acabar
        if done:
            self.inner = kickoff() if _has_routine("kickoff") else None

        return False  # NUNCA pop enquanto kickoff_flag True


class CheatKickoff:
    """
    Cheat no kickoff: vai pro spot e espera. Só termina quando kickoff_flag acabar.
    """
    def __init__(self, spot):
        self.spot = spot

    def run(self, agent):
        #if not agent.kickoff_flag:
        #    return True  # termina só quando kickoff acaba

        relative = self.spot - agent.me.location
        dist = relative.magnitude()
        local = agent.me.local(relative)

        defaultPD(agent, local)

        # chega rápido, mas ao chegar segura posição (não termina o kickoff)
        #if dist > 250:
        #    defaultThrottle(agent, _cap(dist * 2, 0, 2300))
        #    agent.controller.boost = (dist > 1400 and abs(local.x) < 250 and abs(local.y) > 800)
        #else:
        #    defaultThrottle(agent, 0)
        #    agent.controller.boost = False
        #    agent.controller.handbrake = True  # segura bem

        #return False


# ============================================================
# BOT
# ============================================================

class ExampleBot(GoslingAgent):
    def initialize_agent(self):
        super().initialize_agent()
        self.allow_kickoff_reset = True   # permite setar kickoff 1x por kickoff
        self.kickoff_committed = False    # já escolhemos papel nesse kickoff?
        self.kickoff_role = None          # "TAKER" ou "CHEAT"

    def run(agent):
        # ======================
        # Memória (não mexe na base; só adiciona o mínimo necessário)
        # ======================
        if not hasattr(agent, "dbg"):
            agent.dbg = {
                "action": "INIT",
                "role": "UNK",
                "intercept_t": None,
                "intercept_loc": None,
                "shot_kind": None,
                "shot_target": None
            }

        # usado pra evitar loop "chuta -> recua gol" especialmente em 1v1
        if not hasattr(agent, "last_commit_time"):
            agent.last_commit_time = -999.0
            agent.last_commit_kind = None

        me = agent.me
        ball = agent.ball
        s = side(agent.team)

        # ======================
        # Role / rotação (1) - sem mudar o resto
        # ======================
        my_role, i_am_last_man, etas_sorted, goal_sorted, have_mates = _role_and_ranks(agent)
        threat = _threat_level(agent)
        agent.dbg["role"] = my_role

        # ======================
        # RENDER base: linhas
        # ======================
        try:
            left_test_a = Vector3(-4100 * s, ball.location.y, 0)
            left_test_b = Vector3(4100 * s, ball.location.y, 0)
            _safe_line(agent, me.location, left_test_a, (0, 255, 0))
            _safe_line(agent, me.location, left_test_b, (255, 0, 0))
        except Exception:
            pass

        # ======================
        # Se já tem rotina rodando, só render e sai
        # ======================
        if len(agent.stack) > 0:
            _draw_text_3d(agent, me.location + Vector3(0, 0, 120),
                          f"[{agent.dbg['role']}] {agent.dbg['action']}", (255, 255, 255))
            return

        # ======================
        # KICKOFF avançado (8) + FIX término (não ao toque) + suporta 1v1/2v2/3v3
        # ======================
        if agent.kickoff_flag:
            # quem é o taker? menor ETA da equipe (entre friends + me)
            my_is_taker = (etas_sorted[0][0] == me.index)

            if my_is_taker:
                agent.dbg["action"] = "KICKOFF: TAKING (WRAPPED)"
                agent.push(KickoffWrapper())
            else:
                # cheat spot: ligeiramente à frente do meio, do nosso lado
                cheat_spot = Vector3(0, -800 * s, 0)
                agent.dbg["action"] = "KICKOFF: CHEAT (HOLD)"
                agent.push(CheatKickoff(cheat_spot))

            _draw_text_3d(agent, me.location + Vector3(0, 0, 120),
                          f"[{agent.dbg['role']}] {agent.dbg['action']}", (255, 255, 255))
            return

        # ======================
        # Targets e shots (3) + Aerials inteligentes (6) + Wallshot
        # ======================
        targets = {
            "goal": (agent.foe_goal.left_post, agent.foe_goal.right_post),
            "clear": (Vector3(-4100 * s, ball.location.y, 0), Vector3(4100 * s, ball.location.y, 0)),
        }

        shots = find_hits(agent, targets)

        best_shot, best_kind, best_score = _pick_best_shot(agent, shots)

        # Aerial melhor: escolhe um ponto futuro que dá tempo (pedido)
        best_aerial, best_aerial_kind, best_aerial_score = _pick_best_aerial_shot(agent, shots)

        # ======================
        # Intercept info p/ render (círculo / trajeto / seta)
        # ======================
        intercept_time = None
        intercept_loc = None

        # se escolher aerial, render deve usar o intercept dele
        chosen_for_render = best_aerial if best_aerial is not None else best_shot

        if chosen_for_render is not None:
            intercept_time = getattr(chosen_for_render, "intercept_time", None)
            intercept_loc = getattr(chosen_for_render, "ball_location", None)

        agent.dbg["intercept_t"] = intercept_time
        agent.dbg["intercept_loc"] = intercept_loc
        agent.dbg["shot_kind"] = best_kind
        agent.dbg["shot_target"] = _choose_shot_target(agent, best_kind) if best_kind else None

        # ======================
        # DECISÃO PRINCIPAL (mantém sua base; só corrige o loop e melhora aerial/wallshot)
        # ======================

        # commit rule por rotação:
        can_commit_attack = (my_role != "THIRD") or (threat < 0.55)

        # Ajuste importante:
        # O bloco "defesa porque role THIRD" só faz sentido quando EXISTE teammate.
        # Em 1v1, isso causava o loop "chuta -> recua gol".
        third_role_matters = have_mates

        # (1v1) Evitar "chuta -> recua" logo após commit: pequena janela de pressão (sem mudar resto)
        just_committed = (agent.time - agent.last_commit_time) < 1.20

        # ======================
        # WALLSHOT (pedido) - tenta quando bola está na parede e não estamos em perigo alto
        # ======================
        if len(agent.stack) < 1 and _ball_near_wall(agent) and threat < 0.95:
            # se temos boost razoável e podemos comitar (ou é 1v1 e threat baixo), tenta wallshot
            if me.boost >= 25 and (can_commit_attack or not have_mates):
                if _try_push_wallshot(agent):
                    agent.dbg["action"] = "SHOT: WALLSHOT"
                    agent.last_commit_time = agent.time
                    agent.last_commit_kind = "wallshot"
                    # forçar render de alvo wallshot
                    agent.dbg["shot_kind"] = "wallshot"
                    agent.dbg["shot_target"] = _choose_shot_target(agent, "wallshot")

        # ======================
        # AERIAL (pedido): só usa se o aerial escolhido dá tempo
        # ======================
        if len(agent.stack) < 1 and best_aerial is not None:
            # usa aerial apenas se faz sentido (boost + commit ok) e não estamos em perigo absurdo
            if me.boost >= 45 and (can_commit_attack or threat < 0.70):
                agent.dbg["action"] = f"SHOT: AERIAL (SMART) ({best_aerial_kind})"
                agent.push(best_aerial)
                agent.last_commit_time = agent.time
                agent.last_commit_kind = "aerial"
                agent.dbg["shot_kind"] = best_aerial_kind
                agent.dbg["shot_target"] = _choose_shot_target(agent, best_aerial_kind)

        # ======================
        # GROUND SHOT / CLEAR (como antes)
        # ======================
        if len(agent.stack) < 1:
            if best_shot is not None:
                z = getattr(best_shot, "ball_location", Vector3(0, 0, 0)).z

                # se é um shot do tipo wall já vindo do find_hits, também conta
                if _shot_is_wall(best_shot) and threat < 0.95:
                    agent.dbg["action"] = f"SHOT: WALL (HIT) ({best_kind})"
                    agent.push(best_shot)
                    agent.last_commit_time = agent.time
                    agent.last_commit_kind = "wall"
                else:
                    if best_score > 500 and (can_commit_attack or not have_mates):
                        agent.dbg["action"] = f"SHOT: GROUND ({best_kind})"
                        agent.push(best_shot)
                        agent.last_commit_time = agent.time
                        agent.last_commit_kind = best_kind
                    else:
                        agent.dbg["action"] = "POSITION: WAIT / SUPPORT"

        # ======================
        # Sem rotina (ou após decidir não chutar): defesa / boost / support
        # ======================
        if len(agent.stack) < 1:
            # 1v1: se acabou de chutar e threat não é alto, não recuar pro gol — faz pressão/posição no meio
            if (not have_mates) and just_committed and threat < 0.95:
                agent.dbg["action"] = "PRESSURE: POST-SHOT MID"
                # ponto de pressão: um pouco atrás da bola (pra não overcommit), mas não no gol
                pressure = Vector3(ball.location.x, ball.location.y - (1200 * s), 0)
                pressure = Vector3(_cap(pressure.x, -3800, 3800), _cap(pressure.y, -3500, 3500), 0)

                relative = pressure - me.location
                dist = relative.magnitude()
                local = me.local(relative)
                defaultPD(agent, local)

                # (4) speed control + não gastar boost à toa
                desired_speed = _cap(dist * 2.0, 0, 2300)
                dist_ball = (ball.location - me.location).magnitude()
                desired_speed = min(desired_speed, _desired_approach_speed(agent, dist_ball, ball.location.z, ball.velocity.z))
                defaultThrottle(agent, desired_speed)
                agent.controller.boost = (dist > 2400 and abs(local.x) < 240 and abs(local.y) > 900 and me.boost > 20)

            else:
                # DEFESA: antes era "threat > 0.85 or my_role == THIRD"
                # Agora só considera THIRD como defesa obrigatória quando há teammate (2v2/3v3).
                if threat > 0.85 or (my_role == "THIRD" and third_role_matters):
                    ball_towards_our_goal = (ball.velocity.y * s) < -150
                    ball_close_goal = (ball.location - agent.friend_goal.location).magnitude() < 3200

                    if ball_towards_our_goal and ball_close_goal and _has_routine("save"):
                        agent.dbg["action"] = "DEFENSE: SAVE ROUTINE"
                        agent.push(save(agent.friend_goal.location))
                    else:
                        left_dist = (agent.friend_goal.left_post - me.location).magnitude()
                        right_dist = (agent.friend_goal.right_post - me.location).magnitude()
                        target = agent.friend_goal.left_post if left_dist < right_dist else agent.friend_goal.right_post
                        target = Vector3(target.x, target.y, 0)

                        agent.dbg["action"] = "DEFENSE: FAR POST / SHADOW"

                        relative = target - me.location
                        dist = relative.magnitude()
                        local = me.local(relative)
                        defaultPD(agent, local)

                        speed = _cap(dist * 1.8, 0, 2000)
                        defaultThrottle(agent, speed)
                        agent.controller.boost = (dist > 2600 and abs(local.x) < 200 and abs(local.y) > 900 and me.boost > 30)

                # Boost se estiver baixo e não for last man (em 1v1 isso vale também)
                elif me.boost < 30:
                    best_boost = None
                    best_val = -1.0
                    for boost in agent.boosts:
                        if not boost.active:
                            continue
                        if not boost.large:
                            continue

                        me_to_boost = (boost.location - me.location).normalize()
                        boost_to_goal = (agent.friend_goal.location - boost.location).normalize()

                        val = boost_to_goal.dot(me_to_boost)
                        if val > best_val:
                            best_val = val
                            best_boost = boost

                    if best_boost is not None and _has_routine("goto_boost"):
                        agent.dbg["action"] = "RESOURCE: GET BOOST (LARGE)"
                        agent.push(goto_boost(best_boost, agent.friend_goal.location))

                # Support: mid/back post “inteligente”
                else:
                    agent.dbg["action"] = "ROTATE: SUPPORT MID"
                    goal = agent.friend_goal.location
                    ball_to_goal = (goal - ball.location).normalize()
                    support = ball.location + ball_to_goal * 2200
                    support = Vector3(_cap(support.x, -3800, 3800), _cap(support.y, -5100, 5100), 0)

                    relative = support - me.location
                    dist = relative.magnitude()
                    local = me.local(relative)
                    defaultPD(agent, local)

                    desired_speed = _cap(dist * 2.0, 0, 2300)

                    # (4) speed control
                    dist_ball = (ball.location - me.location).magnitude()
                    desired_speed = min(desired_speed, _desired_approach_speed(agent, dist_ball, ball.location.z, ball.velocity.z))

                    defaultThrottle(agent, desired_speed)
                    agent.controller.boost = (dist > 2600 and abs(local.x) < 240 and abs(local.y) > 900 and me.boost > 20)

        # ============================================================
        # RENDER AVANÇADO (com wallshot também)
        # ============================================================

        _draw_text_3d(agent, me.location + Vector3(0, 0, 120),
                      f"[{agent.dbg['role']}] {agent.dbg['action']} | threat={threat:.2f}", (255, 255, 255))

        it = agent.dbg["intercept_t"]
        il = agent.dbg["intercept_loc"]
        st = agent.dbg["shot_target"]

        if it is not None and il is not None:
            # 1) círculo no chão do intercepto
            ground = Vector3(il.x, il.y, 0)
            _draw_circle(agent, ground, radius=260, color=(100, 220, 255), steps=28, z_override=5)

            # 2) seta indicando direção do chute (alvo)
            if st is not None:
                arrow_end = Vector3(st.x, st.y, 0)
                _draw_arrow(agent, ground + Vector3(0, 0, 10), arrow_end + Vector3(0, 0, 10), color=(255, 180, 80))

            # 3) path da bola até o intercepto (no ar)
            dt = max(0.0, it - agent.time)
            if dt > 0.05:
                pts = _sample_ball_path(ball.location, ball.velocity, min(dt, 4.0), step=0.10)

                # cor diferente se for wallshot
                is_wall_context = ("WALL" in agent.dbg["action"].upper())
                path_color = (255, 200, 255) if is_wall_context else (180, 255, 180)

                for i in range(len(pts) - 1):
                    _safe_line(agent, pts[i], pts[i + 1], path_color)

                # marca ponto exato do toque (il)
                _draw_circle(agent, il, radius=120, color=(255, 255, 255), steps=18, z_override=il.z)

                # linha do carro até o intercepto
                _safe_line(agent, me.location, il, (255, 255, 0))

                # render extra wallshot: linha vertical até o chão + círculo no ponto da parede
                if is_wall_context and il.z > 80:
                    _safe_line(agent, Vector3(il.x, il.y, 0), il, (255, 200, 255))
                    _draw_circle(agent, Vector3(il.x, il.y, 0), radius=140, color=(255, 200, 255), steps=18, z_override=10)
