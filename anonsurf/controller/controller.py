import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from ..utils import rel_path

DIR_HERE = rel_path(os.path.relpath(os.path.dirname(__file__)))
DIR_TOR_DATA = os.path.join(os.path.expanduser("~"), f"._tor_data")
DEFAULT_PORT = 10080


class Tor(object):

    _EXECUTOR = ThreadPoolExecutor()

    def __init__(self):
        """
        Creates a Tor proxy process

        :param dict settings: torrc settings (optional)
            key_name,value will be translated to a line of: KeyName str(value)
        """

        self.port = DEFAULT_PORT
        self.control_port = DEFAULT_PORT + 1
        self.dns_port = DEFAULT_PORT + 2
        self.http_tunnel_port = DEFAULT_PORT + 3

        self.binary_path = rel_path('bin/' + sys.platform + '/' + 'tor' + ('' if sys.platform != 'win32' else '.exe'))
        self.process = None
        self.status_bootstrap = 0
        self.debug = False
        self.exception = None
        self.running = False

    def create_config(self, **extra_settings):
        settings = dict(
            socks_port=self.port,
            http_tunnel_port=self.http_tunnel_port,
            control_port=self.control_port,
            dns_port=self.dns_port,
            new_circuit_period=15,
            cookie_authentication=1,
            enforce_distinct_subnets=0,
            data_directory=DIR_TOR_DATA,
        )
        settings.update(extra_settings)
        config_str = ""
        for key, value in settings.items():
            key = "".join(k.capitalize() for k in key.split("_"))
            if isinstance(value, (str, int)):
                config_str += f"{key} {value}\n"
            elif isinstance(value, (list, tuple,)):
                for val in value:
                    config_str += f"{key} {val}\n"
        return config_str

    def is_running(self):
        self.running = False
        if self.process:
            self.running = not self.process.poll()
        return self.running

    def start_nonblocking(self):
        self._EXECUTOR.submit(self.start)

    def start(self):
        """
        starts tor proxy
        :return:
        """
        pattern_get_bootstrap_percent = re.compile("Bootstrapped ([0-9]+)%")

        def set_status(message):
            if self.debug:
                print(message)
            match = pattern_get_bootstrap_percent.search(message)
            if match:
                self.status_bootstrap = int(match.group(1))

        try:
            os.makedirs(DIR_TOR_DATA, exist_ok=True)
            os.chmod(self.binary_path, 0o755)
        except OSError as e:
            raise

        self.process = None

        try:
            si = None
            if hasattr(subprocess, "STARTUPINFO"):
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                [
                    self.binary_path,
                    "__OwningControllerProcess",
                    str(os.getpid()),
                    "-f",
                    "-",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=si,
                env=os.environ,
            )
            torrc = self.create_config()
            self.process.stdin.write(torrc.encode())
            self.process.stdin.close()
            #
            while not self.status_bootstrap == 100:
                message = self.process.stdout.readline().decode()
                set_status(message)
        except Exception as e:
            if self.process:
                self.process.kill()
                self.process.wait()
            self.exception = e
        return self.is_running()

    def stop(self):
        """
        Stops tor proxy
        :return:
        """
        if self.is_running():
            try:
                self.process.terminate()
            except Exception as e:
                print(e)
                self.process.kill()
            self.process.wait(5)
            self.status_bootstrap = 0
        return not self.is_running()

    def __repr__(self):
        return "<{0.__class__.__name__}(running: {0.running}, bootstrapped: {0.status_bootstrap}%)".format(
            self
        )

