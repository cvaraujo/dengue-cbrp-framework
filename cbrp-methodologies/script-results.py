import pandas as pd
import xlsxwriter
import os, sys

class Instance:
    def __init__(self, name):
        self.name = name.split(".")[0]
        # Core instance data
        self.nodes = pd.NA
        self.arcs = pd.NA
        self.blocks = pd.NA

        # Outputs / metrics (nullable when not present in a result file)
        self.attend_blocks = pd.NA
        self.lb = float("nan")
        self.ub = float("nan")
        self.bnb_nodes = pd.NA
        self.frac_cuts = pd.NA
        self.lazy_cuts = pd.NA
        self.solution_time = float("nan")
        self.exec_time = float("nan")

        # Internal helpers (not exported as columns)
        self._route_time = float("nan")
        self._attend_time = float("nan")
        self._attended_blocks_set = set()

    def to_list(self):
        return pd.Series(
            data={
                "Instance": self.name,
                "|V|": self.nodes,
                "|A|": self.arcs,
                "|B|": self.blocks,
                "Attend Blocks": self.attend_blocks,
                "LB": self.lb,
                "UB": self.ub,
                "BnB Nodes": self.bnb_nodes,
                "Frac. Cuts": self.frac_cuts,
                "Lazy Cuts": self.lazy_cuts,
                "Solution Time": self.solution_time,
                "Exec. Time": self.exec_time,
            }
        )


def get_result(folder_name) -> [Instance]:  # type: ignore
    instances = os.listdir(folder_name)
    results = []
    # folders_infos = folder_name.split("-")

    def _parse_numbers_list(s: str):
        # Supports formats like "18,17,16,..." or "18" or "18, 17"
        s = str(s).replace(",", " ")
        parts = [p.strip() for p in s.split() if p.strip() != ""]
        out = []
        for p in parts:
            try:
                out.append(int(p))
            except Exception:
                continue
        return out

    for i in instances:
        f = open(os.path.join(folder_name, i), "r")
        lines = f.readlines()
        i_splitted = i.split("-")
        if len(i_splitted) < 2:
            inst = Instance("SBRP-" + i)
        else:
            if "limoeiro" == i_splitted[1]:
                i = i.replace("limoeiro", "limoeiro-norte")
            inst = Instance(i)

        try:
            for l in lines:
                content = l.strip().split(" ")
                if not content:
                    continue
                key = content[0]
                val = " ".join(content[1:]) if len(content) > 1 else ""

                if key == "N:":
                    inst.nodes = int(content[1])
                elif key == "M:":
                    inst.arcs = int(content[1])
                elif key == "B:":
                    inst.blocks = int(content[1])
                elif key == "Gurobi_Nodes:":
                    inst.bnb_nodes = int(content[1])
                elif content[0] == "LB:":
                    inst.lb = float(content[1])
                elif content[0] == "UB:":
                    inst.ub = float(content[1])
                elif content[0] == "Lazy_cuts:":
                    inst.lazy_cuts = int(content[1])
                elif content[0] == "Frac_cuts:":
                    inst.frac_cuts = int(content[1])
                elif content[0] == "Runtime:":
                    inst.exec_time = float(content[1])
                elif content[0] == "Y:":
                    # Some outputs have one block per line: "Y: 82"
                    # Others may have comma-separated lists: "Y: 18,17,16,..."
                    for b in _parse_numbers_list(val):
                        inst._attended_blocks_set.add(b)
                elif content[0] == "Route_Time:":
                    inst._route_time = float(content[1])
                elif content[0] == "Attend_Time:":
                    inst._attend_time = float(content[1])
        except:
            print(i)

        # Finalize derived fields
        if len(inst._attended_blocks_set) > 0:
            inst.attend_blocks = len(inst._attended_blocks_set)
        else:
            inst.attend_blocks = pd.NA

        # Solution Time: prefer explicit components if present; otherwise Route_Time; otherwise NaN
        if not pd.isna(inst._route_time) and not pd.isna(inst._attend_time):
            inst.solution_time = float(inst._route_time) + float(inst._attend_time)
        elif not pd.isna(inst._route_time):
            inst.solution_time = float(inst._route_time)
        elif not pd.isna(inst._attend_time):
            inst.solution_time = float(inst._attend_time)

        results.append(inst)

    return results


# Default to this repo on Linux; allow override via env var.
results_root = os.environ.get(
    "RESULTS_ROOT",
    "./cbrp-methodologies/walk-results/",
)
output_excel = "results-walk-models.xlsx"

columns = [
    "Instance",
    "|V|",
    "|A|",
    "|B|",
    "Attend Blocks",
    "LB",
    "UB",
    "BnB Nodes",
    "Frac. Cuts",
    "Lazy Cuts",
    "Solution Time",
    "Exec. Time",
]

writer = pd.ExcelWriter(output_excel, engine="xlsxwriter")

# List only folders directly inside results_root
for folder_name in sorted(os.listdir(results_root)):
    folder_path = os.path.join(results_root, folder_name)
    if not os.path.isdir(folder_path):
        continue

    print(f"Processing folder: {folder_name} ...")
    # Assuming get_result returns a list of Instance objects from a folder path.
    results = get_result(folder_path)

    if not results:
        continue

    df = pd.DataFrame([res.to_list() for res in results], columns=columns)
    # Sort by splitting "Instance" on '-' and using positions 0, -2, -1 as sort keys
    def instance_sort_key(s):
        parts = str(s).split('-')
        # Ensure at least 3 parts; pad with empty string if needed
        if len(parts) < 3:
            parts = parts + [''] * (3 - len(parts))
        # Use first part, second to last, last as keys (will be string, sort lexicographically)
        return (parts[0], parts[-2], parts[-1])
    df = df.sort_values(by="Instance", key=lambda col: col.map(instance_sort_key))

    # Format float columns
    def fmt_float(x):
        if pd.isna(x):
            return ""
        return f"{float(x):.3f}".replace(".", ",")

    for col in df.select_dtypes(include="float").columns:
        df[col] = df[col].apply(fmt_float)

    # Sheet names in Excel are limited to 31 chars
    sheet_name = folder_name[:31]
    # Write the DataFrame to its sheet
    df.to_excel(writer, sheet_name=sheet_name, index=False)

writer.close()
