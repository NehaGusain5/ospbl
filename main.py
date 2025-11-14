import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import psutil
import platform
import subprocess
import os
import random
import time
from pathlib import Path
from datetime import datetime

try:
    import win32com.client  # pywin32
    _HAS_PYWIN32 = True
except Exception:
    _HAS_PYWIN32 = False


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Task Manager")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f8fafc")

        self.colors = {
            'primary': '#1e40af', 'success': '#059669', 'warning': '#d97706',
            'danger': '#dc2626', 'surface': '#ffffff', 'text_primary': '#1e293b'
        }

        self.processes = []
        self.max_processes = 10
        self.threshold = 5
        self.current_pid = os.getpid()

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.periodic_update()

    # ------------------- UI -------------------
    def setup_ui(self):
        header = tk.Label(self.root, text="Advanced Task Manager", font=("Segoe UI", 24, "bold"),
                          bg=self.colors['primary'], fg="white")
        header.pack(fill="x")

        stats_frame = tk.Frame(self.root, bg=self.colors['surface'])
        stats_frame.pack(fill="x", padx=20, pady=10)

        self.process_count_label = tk.Label(stats_frame, text="Processes: 0",
                                            font=("Segoe UI", 11, "bold"), bg=self.colors['surface'])
        self.process_count_label.pack(side="left", padx=20)
        self.memory_label = tk.Label(stats_frame, text="Total Memory: 0 MB",
                                     font=("Segoe UI", 11, "bold"), bg=self.colors['surface'])
        self.memory_label.pack(side="left", padx=20)
        self.threshold_label = tk.Label(stats_frame, text=f"Threshold: {self.threshold} MB",
                                        font=("Segoe UI", 11, "bold"), fg=self.colors['warning'], bg=self.colors['surface'])
        self.threshold_label.pack(side="right", padx=20)

        btn_frame = tk.Frame(self.root, bg=self.colors['surface'])
        btn_frame.pack(padx=20, pady=10)
        tk.Button(btn_frame, text="Start Process", command=self.start_process_ui,
                  bg=self.colors['success'], fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Show Processes", command=self.show_processes).pack(side="left", padx=5)
        tk.Button(btn_frame, text="System Monitor", command=self.open_system_monitor,
                  bg=self.colors['primary'], fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Search Process", command=self.open_search_window,
                  bg=self.colors['primary'], fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Kill High Memory", command=self.kill_high_memory,
                  bg=self.colors['warning'], fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Show Heavy", command=self.show_heavy_processes,
                  bg=self.colors['primary'], fg="white").pack(side="left", padx=5)
        # tk.Button(btn_frame, text="Show Scheduling", command=self.show_scheduling_chart,
        #           bg=self.colors['primary'], fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Exit", command=self.exit_app,
                  bg=self.colors['danger'], fg="white").pack(side="left", padx=5)

        columns = ("No", "Command", "PID", "Memory (MB)", "Status")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=200)
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)

    # ------------------- Helpers -------------------
    def is_running(self, pid):
        return psutil.pid_exists(pid)

    def _detect_recent_pid(self, name, delay=1.2):
        time.sleep(delay)
        target = Path(name).stem.lower()
        latest = None
        latest_time = 0
        now = time.time()
        for p in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                pname = (p.info['name'] or '').lower()
                if target in pname and (now - p.info['create_time']) < 8:
                    if p.info['create_time'] > latest_time:
                        latest = p.pid
                        latest_time = p.info['create_time']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return latest

    def start_process(self, cmd):
        if len(self.processes) >= self.max_processes:
            messagebox.showerror("Limit Reached", "Maximum process limit reached.")
            return -1

        cmd = cmd.strip().strip('"')
        if not cmd:
            return -1

        try:
            launch_cmd = cmd
            if cmd.lower().endswith(".lnk") and os.path.exists(cmd) and _HAS_PYWIN32:
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortcut(cmd)
                launch_cmd = shortcut.TargetPath or cmd

            if os.path.exists(launch_cmd):
                os.startfile(launch_cmd)
            else:
                subprocess.Popen(["cmd", "/c", "start", "", cmd], shell=True)

            detected_pid = self._detect_recent_pid(launch_cmd)
            if detected_pid:
                self.processes.append({"pid": detected_pid, "cmd": cmd, "status": "Running"})
                messagebox.showinfo("Process Started", f"✅ '{cmd}' started successfully (PID: {detected_pid})")
            else:
                messagebox.showinfo("Process Started", f"'{cmd}' started but PID not detected yet.")
            self.show_processes()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start process:\n{e}")

    def start_process_ui(self):
        cmd = simpledialog.askstring("Start Process", "Enter process name or full path:", parent=self.root)
        if cmd:
            self.start_process(cmd)

    def show_processes(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        total_mem = 0
        active = []

        for i, proc in enumerate(self.processes):
            pid = proc["pid"]
            if not self.is_running(pid):
                proc["status"] = "Exited"
                continue
            try:
                p = psutil.Process(pid)
                mem = p.memory_info().rss / (1024 * 1024)
                total_mem += mem
                status = "Heavy" if mem > self.threshold else "Normal"
                proc["status"] = "Running"
                active.append(proc)
                self.tree.insert("", "end", values=(i + 1, proc["cmd"], pid, f"{mem:.2f}", status))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc["status"] = "Exited"

        self.processes = active
        self.process_count_label.config(text=f"Processes: {len(active)}")
        self.memory_label.config(text=f"Total Memory: {total_mem:.2f} MB")
        self.update_chart()

    def show_heavy_processes(self):
        heavy = []
        for proc in self.processes:
            if proc["status"] != "Running":
                continue
            try:
                p = psutil.Process(proc["pid"])
                mem = p.memory_info().rss / (1024 * 1024)
                if mem > self.threshold:
                    heavy.append((proc["cmd"], proc["pid"], mem))
            except psutil.NoSuchProcess:
                continue
        if heavy:
            msg = "\n".join([f"{cmd} (PID: {pid}) → {mem:.2f} MB" for cmd, pid, mem in heavy])
            messagebox.showwarning("Heavy Processes", msg)
        else:
            messagebox.showinfo("Info", "No heavy processes found.")

    def kill_high_memory(self):
        killed = []
        for proc in list(self.processes):
            if proc["status"] != "Running":
                continue
            try:
                p = psutil.Process(proc["pid"])
                mem = p.memory_info().rss / (1024 * 1024)
                if mem > self.threshold:
                    p.terminate()
                    p.wait(timeout=3)
                    killed.append((proc["cmd"], proc["pid"], mem))
                    proc["status"] = "Exited"
            except Exception:
                continue
        self.show_processes()
        if killed:
            msg = "\n".join([f"{cmd} (PID:{pid}) → {mem:.2f} MB" for cmd, pid, mem in killed])
            messagebox.showinfo("Terminated", msg)

    def show_scheduling_chart(self):
        if not self.processes:
            messagebox.showinfo("Info", "No running processes.")
            return
        simulated = []
        t = 0
        for proc in self.processes:
            burst = random.randint(2, 8)
            simulated.append((proc["cmd"], t, t + burst))
            t += burst

        fig, ax = plt.subplots(figsize=(8, 4))
        y = 0
        for cmd, start, end in simulated:
            ax.barh(y, end - start, left=start,
                    color=random.choice(["#2563eb", "#059669", "#d97706", "#dc2626"]),
                    edgecolor="black", height=0.4)
            ax.text((start + end) / 2, y, Path(cmd).stem, ha="center", va="center", color="white", fontsize=9)
            y += 1
        ax.set_xlabel("Simulated CPU Time")
        ax.set_yticks([])
        ax.set_title("CPU Scheduling Simulation (FCFS)")
        plt.tight_layout()
        plt.show(block=False)

    def update_chart(self):
        self.ax.clear()
        names, mems, colors = [], [], []
        for p in self.processes:
            if p["status"] != "Running":
                continue
            try:
                mem = psutil.Process(p["pid"]).memory_info().rss / (1024 * 1024)
                names.append(Path(p["cmd"]).stem[:10])
                mems.append(mem)
                colors.append("#d97706" if mem > self.threshold else "#059669")
            except Exception:
                continue
        if mems:
            self.ax.bar(names, mems, color=colors)
        self.ax.axhline(y=self.threshold, color='red', linestyle='--')
        self.ax.set_ylabel("Memory (MB)")
        self.ax.set_title("Process Memory Usage")
        self.canvas.draw()

    def periodic_update(self):
        try:
            self.show_processes()
        except Exception:
            pass
        self.root.after(4000, self.periodic_update)

    def on_closing(self):
        self.root.destroy()

    def exit_app(self):
        self.on_closing()

    def open_system_monitor(self):
        SystemMonitorWindow(self.root)

    def open_search_window(self):
        SearchProcessWindow(self.root)


# -------------------- NEW SEARCH PROCESS WINDOW --------------------
class SearchProcessWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Search System Processes")
        self.window.geometry("1100x700")
        self.window.configure(bg="#f8fafc")

        self.colors = {
            'primary': '#1e40af', 'success': '#059669', 'danger': '#dc2626',
            'surface': '#ffffff', 'warning': '#d97706'
        }

        self.setup_ui()
        self.update_processes()
        self.window.protocol("WM_DELETE_WINDOW", self.go_back)
        self.auto_refresh = True
        self.window.after(2000, self.refresh_loop)

    def setup_ui(self):
        header = tk.Label(self.window, text="Search Running Processes", font=("Segoe UI", 20, "bold"),
                          bg=self.colors['primary'], fg="white")
        header.pack(fill="x")

        search_frame = tk.Frame(self.window, bg=self.colors['surface'])
        search_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(search_frame, text="Search Process:", bg=self.colors['surface']).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=5)
        tk.Button(search_frame, text="Search", command=self.filter_processes,
                  bg=self.colors['success'], fg="white").pack(side="left", padx=5)
        tk.Button(search_frame, text="Back to Main", command=self.go_back,
                  bg=self.colors['danger'], fg="white").pack(side="right")

        columns = ("PID", "Name", "CPU%", "Memory(MB)", "Status")
        self.tree = ttk.Treeview(self.window, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

        self.tree.bind("<<TreeviewSelect>>", self.show_details)

        self.details_label = tk.Label(self.window, text="Select a process to view details",
                                      font=("Segoe UI", 11), bg=self.colors['surface'])
        self.details_label.pack(fill="x", padx=20, pady=10)

    def refresh_loop(self):
        if self.auto_refresh:
            self.update_processes()
        self.window.after(2000, self.refresh_loop)

    def update_processes(self):
        self.processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
            try:
                info = proc.info
                mem = info['memory_info'].rss / (1024 * 1024)
                self.processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu": info['cpu_percent'],
                    "mem": mem,
                    "status": info['status']
                })
            except Exception:
                continue
        self.filter_processes()

    def filter_processes(self):
        query = self.search_var.get().lower()
        for i in self.tree.get_children():
            self.tree.delete(i)
        for proc in self.processes:
            if query in (proc["name"] or "").lower():
                self.tree.insert("", "end", values=(proc["pid"], proc["name"], f"{proc['cpu']:.1f}",
                                                    f"{proc['mem']:.1f}", proc["status"]))

    def show_details(self, event):
        sel = self.tree.selection()
        if sel:
            pid = int(self.tree.item(sel[0])["values"][0])
            try:
                p = psutil.Process(pid)
                info = f"PID: {p.pid}\nName: {p.name()}\nStatus: {p.status()}\nThreads: {p.num_threads()}\n"
                info += f"CPU%: {p.cpu_percent()} | Memory: {p.memory_info().rss / (1024*1024):.2f} MB\n"
                info += f"Start Time: {datetime.fromtimestamp(p.create_time()).strftime('%Y-%m-%d %H:%M:%S')}\n"
                info += f"Executable: {p.exe() if p.exe() else 'N/A'}"
                self.details_label.config(text=info)
            except Exception as e:
                self.details_label.config(text=f"Error fetching process details: {e}")

    def go_back(self):
        self.window.destroy()
        self.parent.lift()
        self.parent.focus_force()
# -------------------- NEW SYSTEM MONITOR WINDOW --------------------
class SystemMonitorWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("System Process Monitor - Top 10 Processes")
        self.window.geometry("1136x768")
        self.window.configure(bg="#f8fafc")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.lift()
        self.window.focus_force()

        self.colors = {
            'primary': '#1e40af', 'danger': '#dc2626', 'accent': '#0ea5e9'
        }

        tk.Label(self.window, text="System Monitor (Top 10 Processes)", font=("Segoe UI", 18, "bold"),
                 bg=self.colors['primary'], fg="white").pack(fill="x")

        self.tree = ttk.Treeview(self.window, columns=("PID", "Name", "CPU%", "Memory%"), show="headings", height=10)
        for col in ("PID", "Name", "CPU%", "Memory%"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200, anchor="center")
        self.tree.pack(fill="x", padx=20, pady=10)

        # Sorting buttons
        sort_frame = tk.Frame(self.window, bg="#f8fafc")
        sort_frame.pack(pady=5)
        tk.Button(sort_frame, text="Sort by CPU%", command=self.sort_by_cpu,
                  bg=self.colors['accent'], fg="white").pack(side="left", padx=10)
        tk.Button(sort_frame, text="Sort by Memory%", command=self.sort_by_memory,
                  bg=self.colors['accent'], fg="white").pack(side="left", padx=10)

        # System control buttons
        control_frame = tk.Frame(self.window, bg="#f8fafc")
        control_frame.pack(pady=5)
        tk.Button(control_frame, text="Shutdown", command=self.shutdown_system,
                  bg=self.colors['danger'], fg="white").pack(side="left", padx=10)
        tk.Button(control_frame, text="Restart", command=self.restart_system,
                  bg=self.colors['danger'], fg="white").pack(side="left", padx=10)

        tk.Button(self.window, text="Back to Main", command=self.go_back,
                  bg=self.colors['danger'], fg="white").pack(pady=10)

        # Visualization setup
        self.fig, self.ax = plt.subplots(figsize=(10, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.window)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)

        self.processes = []
        self.sort_key = 'cpu_percent'
        self.update_processes()
        self.window.after(3000, self.refresh_loop)

    def update_processes(self):
        self.processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                self.processes.append(proc.info)
            except Exception:
                continue
        self.processes.sort(key=lambda p: p[self.sort_key], reverse=True)
        self.refresh_tree()
        self.update_graph()

    def sort_by_cpu(self):
        self.sort_key = 'cpu_percent'
        self.processes.sort(key=lambda p: p['cpu_percent'], reverse=True)
        self.refresh_tree()
        self.update_graph()

    def sort_by_memory(self):
        self.sort_key = 'memory_percent'
        self.processes.sort(key=lambda p: p['memory_percent'], reverse=True)
        self.refresh_tree()
        self.update_graph()

    def refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in self.processes[:10]:
            self.tree.insert("", "end", values=(p['pid'], p['name'], f"{p['cpu_percent']:.1f}", f"{p['memory_percent']:.1f}"))

    def update_graph(self):
        self.ax.clear()
        names = [p['name'] for p in self.processes[:10]]
        values = [p[self.sort_key] for p in self.processes[:10]]
        self.ax.barh(names, values, color="#1e40af")
        self.ax.set_xlabel(f"{self.sort_key.upper()} Usage")
        self.ax.set_title("Top 10 Processes")
        self.ax.invert_yaxis()
        self.fig.tight_layout()
        self.canvas.draw()

    def refresh_loop(self):
        self.update_processes()
        self.window.after(3000, self.refresh_loop)

    def shutdown_system(self):
        if platform.system() == "Windows":
            os.system("shutdown /s /t 1")
        elif platform.system() == "Linux":
            subprocess.call(["shutdown", "-h", "now"])
        elif platform.system() == "Darwin":
            subprocess.call(["sudo", "shutdown", "-h", "now"])

    def restart_system(self):
        if platform.system() == "Windows":
            os.system("shutdown /r /t 1")
        elif platform.system() == "Linux":
            subprocess.call(["shutdown", "-r", "now"])
        elif platform.system() == "Darwin":
            subprocess.call(["sudo", "shutdown", "-r", "now"])

    def go_back(self):
        self.window.destroy()
        self.parent.lift()
        self.parent.focus_force()

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()
