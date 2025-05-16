import asyncio
import json
from time import sleep
import websockets
from pathlib import Path


class Simulation:
    def __init__(
        self,
        server_path: str = "/home/araujo/Documents/gama-1.9.2/headless/gama-headless.sh",
        server_port: int = 6868,
        model: str = "/home/carlos/Documentos/dengue-cbrp-framework/simulation/models/dengue_propagation.gaml",
    ):
        self.server_path = Path(server_path).resolve()
        self.server_port = server_port
        self.model = Path(model).resolve()
        self.websocket_url = f"ws://localhost:{self.server_port}"

    async def _send_message(self, websocket, message: dict):
        msg = json.dumps(message)
        print("Sended: ", msg)
        await websocket.send(msg)

    async def _handle_message(self, websocket, is_batch: bool):
        async for message in websocket:
            response = json.loads(message)
            command = response.get("command", {})
            response_type = response.get("type", "")

            print("Response: ", response)
            if command.get("type") == "load" and response_type == "CommandExecutedSuccessfully":
                print("[INFO] Simulation loaded.")
                experiment_id = response.get("content")
                play_cmd = {
                    "type": "play",
                    "exp_id": experiment_id,
                    "sync": True
                }
                await self._send_message(websocket, play_cmd)

            elif command.get("type") == "play" and response_type == "SimulationEnded":
                print("[INFO] Simulation ended.")
                return

            elif response_type == "SimulationStatusInform":
                if "Batch over" in response.get("content", {}).get("message", ""):
                    print("[INFO] Batch simulation ended.")
                    return

    async def _run(self, parameters: list[dict], is_batch: bool):
        async with websockets.connect(self.websocket_url) as websocket:
            load_cmd = {
                "type": "load",
                "model": str(self.model),
                "experiment": "headless_dengue_propagation" if is_batch else "dengue_propagation",
                "status": True,
                "until": "end_simulation = true",
                "parameters": parameters,
            }

            await self._send_message(websocket, load_cmd)
            await self._handle_message(websocket, is_batch)

    def run_simulation(self, parameters: list[dict], is_batch: bool = False):
        print(f"[INFO] Connecting to GAMA WebSocket at {self.websocket_url}")
        try:
            asyncio.run(self._run(parameters, is_batch))
            print("[INFO] Simulation finished successfully.")
        except Exception as e:
            print(f"[ERROR] Simulation failed: {e}")
