from pico2d import load_image, get_time, clamp, SDL_KEYDOWN, SDL_KEYUP, SDLK_SPACE, SDLK_LEFT, SDLK_RIGHT, SDLK_a
from transitions import Machine, State


class Idle:
    def __init__(self, boy):
        self.boy = boy

    def enter(self):
        self.boy.frame = 0
        self.boy.wait_start_time = get_time()   # IDLE 에 들어올 때마다 5초 타이머 시작

    def exit(self):
        pass

    def do(self):
        self.boy.frame = (self.boy.frame + 1) % 8
        if get_time() - self.boy.wait_start_time > 5:
            self.boy.time_out()

    def draw(self):
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(self.boy.frame * 100, 300, 100, 100, self.boy.x, self.boy.y)
        else:
            self.boy.image.clip_draw(self.boy.frame * 100, 200, 100, 100, self.boy.x, self.boy.y)


class Sleep:
    def __init__(self, boy):
        self.boy = boy

    def enter(self):
        self.boy.frame = 0

    def exit(self):
        pass

    def do(self):
        self.boy.frame = (self.boy.frame + 1) % 8

    def draw(self):
        # 누워서 자는 모습: 90도 회전해서 그린다
        if self.boy.face_dir == 1:
            self.boy.image.clip_composite_draw(self.boy.frame * 100, 300, 100, 100,
                                               3.141592 / 2, '', self.boy.x - 25, self.boy.y - 25, 100, 100)
        else:
            self.boy.image.clip_composite_draw(self.boy.frame * 100, 200, 100, 100,
                                               -3.141592 / 2, '', self.boy.x + 25, self.boy.y - 25, 100, 100)


class Run:
    def __init__(self, boy):
        self.boy = boy

    def enter(self):
        self.boy.frame = 0

    def exit(self):
        pass

    def do(self):
        # 왼쪽/오른쪽은 별도 상태가 아니라 boy.dir 값(-1 또는 1)으로 구분한다
        self.boy.face_dir = self.boy.dir
        self.boy.frame = (self.boy.frame + 1) % 8
        self.boy.x += self.boy.dir * 5
        self.boy.x = clamp(25, self.boy.x, 800 - 25)   # 화면 밖으로 나가지 않게

    def draw(self):
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(self.boy.frame * 100, 100, 100, 100, self.boy.x, self.boy.y)
        else:
            self.boy.image.clip_draw(self.boy.frame * 100, 0, 100, 100, self.boy.x, self.boy.y)


class AutoRun:
    def __init__(self, boy):
        self.boy = boy

    def enter(self):
        self.boy.frame = 0

    def exit(self):
        pass

    def do(self):
        self.boy.frame = (self.boy.frame + 1) % 8

    def draw(self):
        # 이동 방향은 boy.dir(키 입력 상태)이 아니라 face_dir 로 관리한다
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(self.boy.frame * 100, 100, 100, 100, self.boy.x, self.boy.y)
        else:
            self.boy.image.clip_draw(self.boy.frame * 100, 0, 100, 100, self.boy.x, self.boy.y)


class Boy:
    def __init__(self):
        self.x, self.y = 400, 90
        self.frame = 0
        self.face_dir = 1
        self.dir = 0
        self.right_pressed, self.left_pressed = False, False
        self.image = load_image('animation_sheet.png')

        self.IDLE = Idle(self)
        self.SLEEP = Sleep(self)
        self.RUN = Run(self)
        self.AUTO_RUN = AutoRun(self)
        self.states = {'idle': self.IDLE, 'sleep': self.SLEEP, 'run': self.RUN, 'autorun': self.AUTO_RUN}

        states = [
            State('idle', on_enter=self.IDLE.enter, on_exit=self.IDLE.exit),
            State('sleep', on_enter=self.SLEEP.enter, on_exit=self.SLEEP.exit),
            State('run', on_enter=self.RUN.enter, on_exit=self.RUN.exit),
            State('autorun', on_enter=self.AUTO_RUN.enter, on_exit=self.AUTO_RUN.exit),
        ]
        self.machine = Machine(model=self, states=states, initial='idle', ignore_invalid_triggers=True)
        self.machine.add_transition('time_out', 'idle', 'sleep')      # IDLE 5초 경과 -> SLEEP
        self.machine.add_transition('space_down', 'sleep', 'idle')    # SLEEP 에서 SPACE -> IDLE
        self.machine.add_transition('arrow_down', 'idle', 'run')      # IDLE 에서 방향키 누름 -> RUN
        self.machine.add_transition('arrow_down', 'sleep', 'run')     # SLEEP 에서 방향키 누름 -> RUN
        self.machine.add_transition('arrow_up', 'run', 'idle')        # RUN 에서 방향키 뗌 -> IDLE
        self.machine.add_transition('a_down', 'idle', 'autorun')      # IDLE 에서 A 키 -> AUTORUN

        self.states[self.state].enter()   # 초기 상태는 전이 없이 시작하므로 직접 enter 호출

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN and event.key == SDLK_SPACE:
            self.space_down()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_a:
            self.a_down()
        elif event.type in (SDL_KEYDOWN, SDL_KEYUP) and event.key in (SDLK_LEFT, SDLK_RIGHT):
            pressed = event.type == SDL_KEYDOWN
            if event.key == SDLK_RIGHT:
                self.right_pressed = pressed
            else:
                self.left_pressed = pressed
            self.dir = self.right_pressed - self.left_pressed

            # 방향키가 눌려 있으면 RUN, 모두 떼어졌거나 양쪽을 다 누르면 IDLE
            if self.dir != 0:
                self.arrow_down()
            else:
                self.arrow_up()

    def update(self):
        self.states[self.state].do()

    def draw(self):
        self.states[self.state].draw()
