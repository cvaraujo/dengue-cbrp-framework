import asyncio
import json
import websockets
import os
import logging

logging.basicConfig(level=logging.INFO)


class Simulation:
    def __init__(self,
                 server_path="/home/araujo/Documents/gama-1.9.2/headless/gama-headless.sh",
                 server_port="6868",
                 model="/home/araujo/Documents/dengue-arp-simulation/models/dengue_propagation.gaml"):
        self.server_path = os.path.abspath(server_path)
        self.server_port = server_port
        self.model = os.path.abspath(model)

    async def run_simulation(self, parameters, is_batch=False):
        uri = f"ws://localhost:{self.server_port}"
        ended = asyncio.Event()

        async def on_message(ws, message):
            decode = json.loads(message)

            if "command" in decode:
                if decode["command"]["type"] == "load" and decode["type"] == "CommandExecutedSuccessfully":
                    logging.info("Simulation loaded...")
                    experiment_id = decode["content"]
                    play_cmd = {
                        "type": "play",
                        "exp_id": experiment_id,
                        "sync": True
                    }
                    await ws.send(json.dumps(play_cmd))

                elif decode["command"]["type"] == "play" and decode["type"] == "SimulationEnded":
                    logging.info("Simulation ended...")
                    await ws.close()
                    ended.set()

            elif decode.get("type") == "SimulationStatusInform" and "Batch over" in decode["content"].get("message", ""):
                logging.info("[BATCH] Simulation ended...")
                await ws.close()
                ended.set()

        async with websockets.connect(uri) as ws:
            # Prepare load command
            cmd = {
                "type": "load",
                "model": self.model,
                "experiment": "headless_dengue_propagation" if is_batch else "dengue_propagation",
                "status": True,
                "until": "end_simulation = true",
                "parameters": parameters
            }

            await ws.send(json.dumps(cmd))

            async def receiver():
                try:
                    async for message in ws:
                        await on_message(ws, message)
                except websockets.ConnectionClosed:
                    logging.info("WebSocket connection closed")

            receiver_task = asyncio.create_task(receiver())
            await ended.wait()
            receiver_task.cancel()
            logging.info("[Simulation] Finished the run!")

    def start(self, parameters, is_batch=False):
        asyncio.run(self.run_simulation(parameters, is_batch))
