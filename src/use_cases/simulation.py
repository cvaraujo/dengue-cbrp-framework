import asyncio, json, websockets, psutil, subprocess
from math import e
from venv import logger
from pathlib import Path


class Simulation:
    def __init__(
        self,
        server_path: str = "/home/carlos/Documentos/GAMA_1.9.2_Linux_with_JDK/headless/gama-headless.sh",
        server_port: str = "6869",
        model: str = "/home/carlos/Documentos/dengue-cbrp-framework/simulation/models/dengue_propagation.gaml",
    ):
        self.server_path = Path(server_path).resolve()
        self.server_port = server_port
        self.model = Path(model).resolve()
        self.websocket_url = f"ws://localhost:{self.server_port}"
        self._run_gama_headless_with_socket()
        logger.info(f"[*] Connecting to GAMA WebSocket at {self.websocket_url}")


    async def _send_message(self, websocket, message: dict):
        msg = json.dumps(message)
        await websocket.send(msg)

    async def _handle_message(self, websocket, is_batch: bool):
        async for message in websocket:
            response = json.loads(message)
            command = response.get("command", {})
            response_type = response.get("type", "")

            if (
                command.get("type") == "load"
                and response_type == "CommandExecutedSuccessfully"
            ):
                logger.info("[*] Simulation loaded.")
                experiment_id = response.get("content")
                play_cmd = {"type": "play", "exp_id": experiment_id, "sync": True}
                await self._send_message(websocket, play_cmd)

            elif command.get("type") == "play" and response_type == "SimulationEnded":
                logger.info("[*] Simulation ended.")
                return

            elif response_type == "SimulationStatusInform":
                if "Batch over" in response.get("content", {}).get("message", ""):
                    logger.info("[*] Batch simulation ended.")
                    return

    async def _run(self, parameters: list[dict], is_batch: bool, short: bool = False):
        async with websockets.connect(self.websocket_url) as websocket:
            experiment = "dengue_propagation"
            if is_batch:
                experiment = (
                    "short_headless_dengue_propagation"
                    if short
                    else "long_headless_dengue_propagation"
                )
            load_cmd = {
                "type": "load",
                "model": str(self.model),
                "experiment": experiment,
                "status": True,
                "until": "end_simulation = true",
                "parameters": parameters,
            }

            await self._send_message(websocket, load_cmd)
            await self._handle_message(websocket, is_batch)

    def _run_gama_headless_with_socket(self):
        try:
            if self.is_gama_running():
                logger.info("[*] GAMA is already running.")
                return

            logger.info("[*] Starting GAMA...")
            subprocess.Popen(
                [self.server_path, "-socket", self.server_port],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            logger.error(f"Error: the '{self.server_path}' file was not founded.")
        except PermissionError:
            logger.error(f"Error: permission denied to run '{self.server_path}'.")
        except Exception as e:
            logger.error(f"Error to start GAMA: {e}")

    def run_simulation(
        self, parameters: list[dict], is_batch: bool = False, is_short: bool = False
    ):
        try:
            asyncio.run(self._run(parameters, is_batch, is_short))
        except Exception as e:
            logger.error(f"[!] Simulation failed: {e}")
            exit(1)

    def is_gama_running(self, process_name: str = "gama-headless"):
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            try:
                if process_name in proc.info["name"]:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def kill_gama_headless(self):
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline")
                if cmdline and any("GAMA_1.9.2_" in part for part in cmdline):
                    logger.info(
                        f"Ending GAMA process {proc.info['pid']}: {' '.join(proc.info['cmdline'])}"
                    )
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
