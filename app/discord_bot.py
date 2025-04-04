import random
from signal import SIGTERM

from pexpect import popen_spawn, EOF, TIMEOUT

from constants import *
from helpers import *

# ------------------------------------------------------------------------------------ #

logger = logging.getLogger(LOGGER)

PROCESS_ID = os.getpid()


# ------------------------------------------------------------------------------------ #
class DiscordBotLocal:
    def get_name(self, default) -> str:
        config_path = (Path(self.app.game_entry.get()) / 'discord/config.json').resolve()
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                name = json.load(f).get('name')
                return name or default
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            logger.warning('Discord bot name not found. Using default.')
            return default
    def __init__(self, app, bot_frame) -> None:
        # seria onde ficaria o equivalente de childprocces do node
        self.process = None
        # acho que é uma instancia da main
        self.app = app
        # o frame é a tela em que ele aparece, de acordo com a bilbioteca de gui usada pelo diogo
        self.bot_frame = bot_frame
        self.task = None
        self.bot_name = self.get_name('DiscordBot')

    # na doc o poll() retorna None se ainda tiver rodando, o proccess é auto explicativo
    def is_running(self):
        return self.process and self.process.proc.poll() is None or False

    def get_arguments(self):
        cwd = (Path().resolve()/ "discord").resolve()
        args = f'node {(cwd / "index.js").resolve()}'
        args = args.split()
        return args, str(cwd)

    def start(self):
        if self.is_running():
            logger.warning(f"Shard {self.bot_name} is already running...")
            return
        logger.info(f"Starting {self.bot_name} shard...")
        self.bot_frame.set_starting()
        args, cwd = self.get_arguments()

        # logger.debug("Starting server with these arguments: %s", " ".join(args))
        # This is HORRIBLE, but it works (Pyinstaller --noconcole + subprocess issue)
        # é oq tem pra hoje, simula um console bem dizer
        with StdoutMock() as sys.stdout:
            # spawna oq seria o child process do node
            self.process = popen_spawn.PopenSpawn(args, cwd=cwd, encoding="utf-8", codec_errors="ignore")
        # a cada ~60ms isso roda a função "handle_output" é semelhar a um runanble/thread do java
        self.task = PeriodicTask(self.app, random.randrange(50, 70), self.handle_output, initial_time=0)

    def on_stopped(self):
        logger.info(f"{self.shard} shard is down...")

        if self.task:
            self.task.kill()

        self.bot_frame.set_offline()

        self.process = None
        self.task = None

    def stop(self):
        if not self.is_running():
            return

        if self.bot_frame.is_starting() or self.bot_frame.is_restarting():
            self.process.kill(SIGTERM)
            self.on_stopped()

        elif self.bot_frame.is_online():
            self.bot_frame.set_stopping()
            self.execute_command(ANNOUNCE_STR.format(msg="Bot desligando, e naipe, e naipe!"), log=False)
            logger.info(f"Stopping {self.bot_name} bot...")

    # po vei isso le o output do meu bot que eu so quero que apareça la no frame do console
    # so tenho que saber se é esse metodo que atualiza o console la, se for deixo
    # se nao eu apago isso
    def handle_output(self):
        """
        Reads all new data from shard.process and handle key phases.
        Should be used in a PeriodicTask.

        Returns:
            success (bool, None): if not True, stops the loop. See PeriodicTask._execute.
            newtime: (int, float, None): override PeriodicTask.time for the next call, if not None. See PeriodicTask._execute.
        """
        if not self.is_running():
            self.on_stopped()
            self.app.stop_shards()

            return False, None

        text = None

        try:
            text = self.process.read_nonblocking(size=9999, timeout=None)

        except (EOF, TIMEOUT):
            return True, 500

        if not text:
            return True, None

        # Atualiza o console no frame.
        self.bot_frame.add_text_to_log_screen(text)
        return True, None
