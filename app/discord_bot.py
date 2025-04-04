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
    def __init__(self, app, bot_frame) -> None:
        # seria onde ficaria o equivalente de childprocces do node
        self.process = None
        # acho que é uma instancia da main
        self.app = app
        # o frame é a tela em que ele aparece, de acordo com a bilbioteca de gui usada pelo diogo
        self.bot_frame = bot_frame
        self.bot = bot_frame.code
        self.task = None

    # na doc o poll() retorna None se ainda tiver rodando, o proccess é auto explicativo
    def is_running(self):
        return self.process and self.process.proc.poll() is None or False

    def get_arguments(self):
        vox_directory = Path(self.app.game_entry.get())
        cwd = (vox_directory / "bot").resolve()
        args = f'node {(cwd / "index.js").resolve()}'
        args = args.split()
        return args, str(cwd)

    def start(self):
        if self.is_running():
            logger.warning(f"Shard {self.bot} is already running...")
            return
        logger.info(f"Starting {self.bot} shard...")
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

    def command_payload(self, command, shard, log=True):
        if shard is None:
            logger.error(f"Shard {self.shard} is not registered in shard list...")
            # TODO: Criar um popup ou outro tipo de alerta visual no futuro
            return

        if log:
            logger.info(f"({self.shard}) Executing console command: {command}")

        try:
            shard.server.execute_command(command)
        except OSError as e:
            logger.error(
                f"OSError during DedicatedServerShard [{self.shard}] execute_command function! "
                f"Command: '{command}'. Actual error: '{e}'"
            )

    def execute_command(self, command, shard_code, log=True):
        shard_manager = self.app.shard_group

        if not self.is_running():
            return

        if shard_code == "_all":
            for shard in shard_manager.get_shards():
                self.command_payload(command, shard, log)
        else:
            self.command_payload(command, shard_manager.get_shard(shard_code), log)

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
            logger.info(f"Stopping {self.bot} bot...")

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

        # Futuramente pode servir de algo: self.handle_output_keywords(text=text)
        return True, None


""" é basicamente um ExceptionHandler de acordo com oq apareçe la no console
    # eu posso deixar pra futuramente fazer algo assim, mas fica comentado na versao do bot
    def handle_output_keywords(self, text):
        if "E_INVALID_TOKEN" in text or "E_EXPIRED_TOKEN" in text:
            logger.error("Invalid Token: E_INVALID_TOKEN or E_EXPIRED_TOKEN")

            self.app.token_entry.toggle_warning(False)
            self.app.stop_shards()

            self.app.error_popup.create(STRINGS.ERROR.TOKEN_INVALID)

        elif "Received world rollback request" in text:
            logger.info(f"{self.shard} received a rollback request...")

            self.app.shard_group.set_all_shards_restarting()

        elif "uploads added to server." in text:
            logger.info(f"{self.shard} is now online!")

            self.bot_frame.set_online()

            self.app.token_entry.toggle_warning(True)

        elif "SOCKET_PORT_ALREADY_IN_USE" in text:
            logger.error("Invalid cluster path or ports in use: SOCKET_PORT_ALREADY_IN_USE.")

            self.app.stop_shards()

            cluster_directory = Path(self.app.cluster_entry.get())
            config_file = cluster_directory

            ports = []

            for shard in get_shard_names(cluster_directory):
                config_file = cluster_directory / shard / "server.ini"

                if config_file.exists:
                    port = get_key_from_ini_file(config_file, "server_port")
                    ports.append(f"{port} ({shard})")

            self.app.error_popup.create(STRINGS.ERROR.PORTS.format(ports=", ".join(ports)))

        elif "[Error] Server failed to start!" in text:
            logger.error(f"{self.bot_frame.code} failed to start!")

            self.app.stop_shards()

            self.app.error_popup.create(STRINGS.ERROR.GENERAL)

        # Runs mainly on master.
        elif "]: Shutting down" in text:
            logger.info(f"{self.bot_frame.code} was shut down... Stopping other shards.")

            self.bot_frame.set_stopping()
            self.app.stop_shards()

        elif self.bot_frame.is_master and "Sim paused" in text:
            self.execute_command(load_lua_file("onserverpaused"), log=False)
"""
