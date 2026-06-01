import os
import subprocess
from pathlib import Path

commands = []

# python3 src/main.py docker default 1800 10 500 AS 700 2017-01-08 2017-01-15 /app/run_DEFAULT_10_500_AS_700_2017-01-08_2017-01-15/

# Path("stochastic-results-sa").mkdir(parents=True, exist_ok=True)

for stochastic_evaluation in ["default", "proportional"]:
    for max_run_time in [600, 1800, 3600]:
        for elite_size in [5, 10, 20]:
            for max_iters_with_surrogate in [100, 500, 1000]:
                for city in ["AS"]:
                    for map_size in [700, 1000]:
                        for start_date in ["2017-01-15"]:
                            for end_date in ["2017-01-22"]:
                                output_folder = f"simheuristic-runs/{stochastic_evaluation}-{max_run_time}-{elite_size}-{max_iters_with_surrogate}-{city}-{map_size}-{start_date}-{end_date}"
                                Path(output_folder).mkdir(parents=True, exist_ok=True)
                                command = f"python3 src/main.py docker {stochastic_evaluation} {max_run_time} {elite_size} {max_iters_with_surrogate} {city} {map_size} {start_date} {end_date} {output_folder}"
                                commands.append(command)
                        for start_date in ["2017-01-29"]:
                            for end_date in ["2017-02-05"]:
                                output_folder = f"simheuristic-runs/{stochastic_evaluation}-{max_run_time}-{elite_size}-{max_iters_with_surrogate}-{city}-{map_size}-{start_date}-{end_date}"
                                Path(output_folder).mkdir(parents=True, exist_ok=True)
                                command = f"python3 src/main.py docker {stochastic_evaluation} {max_run_time} {elite_size} {max_iters_with_surrogate} {city} {map_size} {start_date} {end_date} {output_folder}"
                                commands.append(command)

                for city in ["LM"]:
                    for map_size in [1000, 2000]:
                        for start_date in ["2020-07-19"]:
                            for end_date in ["2020-07-26"]:
                                output_folder = f"simheuristic-runs/{stochastic_evaluation}-{max_run_time}-{elite_size}-{max_iters_with_surrogate}-{city}-{map_size}-{start_date}-{end_date}"
                                Path(output_folder).mkdir(parents=True, exist_ok=True)
                                command = f"python3 src/main.py docker {stochastic_evaluation} {max_run_time} {elite_size} {max_iters_with_surrogate} {city} {map_size} {start_date} {end_date} {output_folder}"
                                commands.append(command)
                        for start_date in ["2020-07-26"]:
                            for end_date in ["2020-08-02"]:
                                output_folder = f"simheuristic-runs/{stochastic_evaluation}-{max_run_time}-{elite_size}-{max_iters_with_surrogate}-{city}-{map_size}-{start_date}-{end_date}"
                                Path(output_folder).mkdir(parents=True, exist_ok=True)
                                command = f"python3 src/main.py docker {stochastic_evaluation} {max_run_time} {elite_size} {max_iters_with_surrogate} {city} {map_size} {start_date} {end_date} {output_folder}"
                                commands.append(command)

for c in commands:
    print(c)
    p = subprocess.Popen(c, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    msg, err = p.communicate()
    if msg:
        print(msg)
    print("OK!!")
