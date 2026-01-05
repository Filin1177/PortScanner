import socket
import threading
import subprocess
import platform
import webbrowser
import requests
import http.server
import socketserver
import time
import json
from datetime import datetime
from urllib.parse import urlparse
import ipaddress
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os

# ==================== ИНСТРУМЕНТЫ ====================

class ScannerTools:
    def __init__(self, main_app=None):
        self.main_app = main_app
        self.http_server = None
        self.server_thread = None
        self.server_running = False

    def log(self, message, level='INFO'):
        """Логирование (прокси к основному приложению)"""
        if self.main_app and hasattr(self.main_app, 'log'):
            self.main_app.log(message, level)

    # ==================== ИНСТРУМЕНТЫ СЕТИ ====================

    def scan_local_network(self, dialog=None):
        """Сканирование локальной сети"""
        try:
            if not dialog:
                dialog = tk.Toplevel()
                dialog.title("Сканирование сети")
                dialog.geometry("500x400")

            ttk.Label(dialog, text="Сканирование локальной сети", font=('Arial', 12)).pack(pady=10)

            output_text = scrolledtext.ScrolledText(dialog, height=15)
            output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            def start_scan():
                output_text.delete(1.0, tk.END)
                output_text.insert(tk.END, "Начинаю сканирование сети...\n")

                # Получаем локальный IP
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(('8.8.8.8', 80))
                    local_ip = s.getsockname()[0]
                    s.close()

                    # Определяем подсеть
                    ip_parts = local_ip.split('.')
                    subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"

                    output_text.insert(tk.END, f"Локальный IP: {local_ip}\n")
                    output_text.insert(tk.END, f"Подсеть: {subnet}.0/24\n\n")

                    # Сканируем первые 20 адресов
                    for i in range(1, 21):
                        ip = f"{subnet}.{i}"
                        if ip != local_ip:
                            threading.Thread(target=self.ping_ip_gui, args=(ip, dialog, output_text), daemon=True).start()

                except Exception as e:
                    output_text.insert(tk.END, f"Ошибка: {e}\n")

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=10)

            ttk.Button(btn_frame, text="Начать сканирование", command=start_scan).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        except Exception as e:
            self.log(f"Ошибка сканирования сети: {e}", 'ERROR')

    def ping_ip_gui(self, ip, dialog, output_text):
        """Пинг IP для GUI"""
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            result = subprocess.run(['ping', param, '1', '-w', '1000', ip],
                                    capture_output=True, text=True)

            if "TTL" in result.stdout or "ttl" in result.stdout.lower():
                dialog.after(0, lambda: output_text.insert(tk.END, f"✓ {ip} - доступен\n"))

                # Проверяем порт 80
                try:
                    sock = socket.socket()
                    sock.settimeout(1)
                    if sock.connect_ex((ip, 80)) == 0:
                        dialog.after(0, lambda: output_text.insert(tk.END, f"  → Веб-сервер на {ip}:80\n"))
                    sock.close()
                except:
                    pass
        except:
            pass

    def ping_host(self, ip):
        """Пинг хоста"""
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            result = subprocess.run(['ping', param, '1', '-w', '1000', ip],
                                    capture_output=True, text=True)

            if "TTL" in result.stdout or "ttl" in result.stdout.lower():
                return True
        except:
            pass
        return False

    # ==================== ИНСТРУМЕНТЫ ПОРТОВ ====================

    def open_port_tool(self):
        """Инструмент открытия порта"""
        dialog = tk.Toplevel()
        dialog.title("Открытие порта")
        dialog.geometry("500x400")

        ttk.Label(dialog, text="Открытие порта в брандмауэре", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Номер порта:").grid(row=0, column=0, sticky=tk.W, pady=5)
        port_entry = ttk.Entry(main_frame, width=20)
        port_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(main_frame, text="Протокол:").grid(row=1, column=0, sticky=tk.W, pady=5)
        protocol_var = tk.StringVar(value="TCP")
        ttk.Combobox(main_frame, textvariable=protocol_var,
                     values=["TCP", "UDP"], state='readonly', width=18).grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(main_frame, text="Направление:").grid(row=2, column=0, sticky=tk.W, pady=5)
        direction_var = tk.StringVar(value="Входящий")
        ttk.Combobox(main_frame, textvariable=direction_var,
                     values=["Входящий", "Исходящий", "Оба"],
                     state='readonly', width=18).grid(row=2, column=1, pady=5, padx=5)

        ttk.Label(main_frame, text="Имя правила:").grid(row=3, column=0, sticky=tk.W, pady=5)
        rule_name = ttk.Entry(main_frame, width=20)
        rule_name.grid(row=3, column=1, pady=5, padx=5)
        rule_name.insert(0, "MyCustomPort")

        output_text = scrolledtext.ScrolledText(main_frame, height=8)
        output_text.grid(row=4, column=0, columnspan=2, sticky=tk.NSEW, pady=10, padx=5)

        main_frame.grid_rowconfigure(4, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        def open_port():
            try:
                port = int(port_entry.get())
                protocol = protocol_var.get()
                direction = direction_var.get()
                rule = rule_name.get()

                output_text.delete(1.0, tk.END)
                output_text.insert(tk.END, f"Открытие порта {port}/{protocol}...\n")

                if platform.system() == "Windows":
                    commands = []

                    if direction in ["Входящий", "Оба"]:
                        cmd = ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                               f'name={rule}In',
                               'dir=in',
                               'action=allow',
                               f'protocol={protocol}',
                               f'localport={port}',
                               'profile=any']
                        commands.append(("Входящее правило", cmd))

                    if direction in ["Исходящий", "Оба"]:
                        cmd = ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                               f'name={rule}Out',
                               'dir=out',
                               'action=allow',
                               f'protocol={protocol}',
                               f'localport={port}',
                               'profile=any']
                        commands.append(("Исходящее правило", cmd))

                    for rule_name_text, cmd in commands:
                        try:
                            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                            if result.returncode == 0:
                                output_text.insert(tk.END, f"✓ {rule_name_text} добавлено\n")
                            else:
                                output_text.insert(tk.END, f"✗ {rule_name_text}: {result.stderr}\n")
                        except Exception as e:
                            output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

                    messagebox.showinfo("Успех", f"Порт {port} открыт")
                    self.log(f"Открыт порт {port}/{protocol} ({direction})", 'INFO')

                else:
                    output_text.insert(tk.END, "Для Linux/Mac используйте:\n")
                    output_text.insert(tk.END, "sudo ufw allow {port}/{protocol}\n")
                    output_text.insert(tk.END, "или\n")
                    output_text.insert(tk.END, "sudo iptables -A INPUT -p {protocol} --dport {port} -j ACCEPT\n")
                    messagebox.showinfo("Информация", "На Linux/Mac используйте iptables/ufw")

            except ValueError:
                output_text.insert(tk.END, "✗ Ошибка: Введите корректный номер порта\n")
            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")
                self.log(f"Ошибка открытия порта: {e}", 'ERROR')

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Открыть порт", command=open_port).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Тестировать порт",
                   command=lambda: self.test_port(port_entry.get() if port_entry.get() else "80")).pack(side=tk.LEFT,
                                                                                                        padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def test_port(self, port_str):
        """Тестирование порта"""
        try:
            port = int(port_str)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)

            result = sock.connect_ex(('localhost', port))
            sock.close()

            if result == 0:
                messagebox.showinfo("Тест порта", f"Порт {port} открыт на localhost")
            else:
                messagebox.showinfo("Тест порта", f"Порт {port} закрыт на localhost")
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректный номер порта")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def close_port_tool(self):
        """Закрытие порта"""
        dialog = tk.Toplevel()
        dialog.title("Закрытие порта")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Закрытие порта в брандмауэре", font=('Arial', 12)).pack(pady=10)

        # Получаем список открытых портов
        open_ports = self.get_open_ports_list()

        list_frame = ttk.LabelFrame(dialog, text="Открытые порты на этом компьютере", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ('port', 'protocol', 'state', 'process')
        tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)

        tree.heading('port', text='Порт')
        tree.heading('protocol', text='Протокол')
        tree.heading('state', text='Состояние')
        tree.heading('process', text='Процесс')

        tree.column('port', width=80)
        tree.column('protocol', width=80)
        tree.column('state', width=100)
        tree.column('process', width=200)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for port_info in open_ports:
            tree.insert('', 'end', values=(
                port_info.get('port', ''),
                port_info.get('protocol', 'TCP'),
                port_info.get('state', 'LISTENING'),
                port_info.get('process', 'Неизвестно')
            ))

        input_frame = ttk.Frame(dialog)
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(input_frame, text="Или введите порт вручную:").pack(side=tk.LEFT, padx=5)
        port_entry = ttk.Entry(input_frame, width=15)
        port_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(input_frame, text="Протокол:").pack(side=tk.LEFT, padx=5)
        protocol_var = tk.StringVar(value="TCP")
        protocol_combo = ttk.Combobox(input_frame, textvariable=protocol_var,
                                      values=["TCP", "UDP"], state='readonly', width=8)
        protocol_combo.pack(side=tk.LEFT, padx=5)

        output_text = scrolledtext.ScrolledText(dialog, height=6)
        output_text.pack(fill=tk.X, padx=10, pady=5)

        def close_selected_port():
            selection = tree.selection()
            if selection:
                item = tree.item(selection[0])
                port = item['values'][0]
                protocol = item['values'][1]
                self.close_port(port, protocol, output_text)
            else:
                messagebox.showwarning("Внимание", "Выберите порт из списка")

        def close_manual_port():
            port = port_entry.get()
            protocol = protocol_var.get()

            if port and port.isdigit():
                self.close_port(int(port), protocol, output_text)
            else:
                messagebox.showwarning("Внимание", "Введите корректный номер порта")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Закрыть выбранный порт", command=close_selected_port).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть порт вручную", command=close_manual_port).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Обновить список",
                   command=lambda: self.refresh_port_list(tree)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def get_open_ports_list(self):
        """Получение списка открытых портов"""
        open_ports = []

        try:
            if platform.system() == "Windows":
                result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, shell=True)
                lines = result.stdout.split('\n')

                for line in lines:
                    if 'LISTENING' in line and 'TCP' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            local_addr = parts[1]
                            if ':' in local_addr:
                                port = local_addr.split(':')[-1]
                                pid = parts[-1]

                                try:
                                    process_result = subprocess.run(
                                        ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                                        capture_output=True, text=True, shell=True
                                    )
                                    process_name = "Неизвестно"
                                    if process_result.stdout.strip():
                                        process_parts = process_result.stdout.strip().split(',')
                                        if len(process_parts) > 0:
                                            process_name = process_parts[0].replace('"', '')
                                except:
                                    process_name = "Неизвестно"

                                open_ports.append({
                                    'port': port,
                                    'protocol': 'TCP',
                                    'state': 'LISTENING',
                                    'process': process_name,
                                    'pid': pid
                                })
            else:
                result = subprocess.run(['netstat', '-tulpn'], capture_output=True, text=True, shell=True)
                lines = result.stdout.split('\n')

                for line in lines:
                    if 'LISTEN' in line:
                        parts = line.split()
                        if len(parts) >= 6:
                            proto = parts[0]
                            local_addr = parts[3]
                            if ':' in local_addr:
                                port = local_addr.split(':')[-1]
                                pid_process = parts[-1]

                                open_ports.append({
                                    'port': port,
                                    'protocol': proto.upper(),
                                    'state': 'LISTEN',
                                    'process': pid_process
                                })

        except Exception as e:
            self.log(f"Ошибка получения списка портов: {e}", 'ERROR')

        return open_ports[:50]

    def refresh_port_list(self, tree):
        """Обновление списка портов"""
        for item in tree.get_children():
            tree.delete(item)

        open_ports = self.get_open_ports_list()

        for port_info in open_ports:
            tree.insert('', 'end', values=(
                port_info.get('port', ''),
                port_info.get('protocol', 'TCP'),
                port_info.get('state', 'LISTENING'),
                port_info.get('process', 'Неизвестно')
            ))

    def close_port(self, port, protocol="TCP", output_text=None):
        """Закрытие порта"""
        try:
            if output_text:
                output_text.delete(1.0, tk.END)
                output_text.insert(tk.END, f"Закрытие порта {port}/{protocol}...\n")

            if platform.system() == "Windows":
                rule_patterns = [
                    f"OpenPort{port}",
                    f"Port{port}",
                    f"CustomPort{port}",
                    f"MyCustomPort{port}"
                ]

                deleted_rules = []

                for pattern in rule_patterns:
                    for direction in ['In', 'Out']:
                        rule_name = f"{pattern}{direction}"
                        try:
                            check_cmd = ['netsh', 'advfirewall', 'firewall', 'show', 'rule',
                                         f'name={rule_name}']
                            result = subprocess.run(check_cmd, capture_output=True, text=True, shell=True)

                            if "Указанное правило не найдено" not in result.stdout and "No rules match" not in result.stdout:
                                del_cmd = ['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                                           f'name={rule_name}']
                                result = subprocess.run(del_cmd, capture_output=True, text=True, shell=True)

                                if result.returncode == 0:
                                    if output_text:
                                        output_text.insert(tk.END, f"✓ Удалено правило: {rule_name}\n")
                                    deleted_rules.append(rule_name)
                                else:
                                    if output_text:
                                        output_text.insert(tk.END, f"✗ Ошибка удаления {rule_name}: {result.stderr}\n")
                        except Exception as e:
                            if output_text:
                                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

                if deleted_rules:
                    messagebox.showinfo("Успех", f"Порт {port} закрыт. Удалено правил: {len(deleted_rules)}")
                    self.log(f"Закрыт порт {port}/{protocol}", 'INFO')
                else:
                    messagebox.showinfo("Информация", "Правила для этого порта не найдены")

            else:
                if output_text:
                    output_text.insert(tk.END, "Для Linux/Mac используйте:\n")
                    output_text.insert(tk.END, "sudo ufw delete allow {port}/{protocol}\n")
                    output_text.insert(tk.END, "или\n")
                    output_text.insert(tk.END, "sudo iptables -D INPUT -p {protocol} --dport {port} -j ACCEPT\n")
                messagebox.showinfo("Информация", "На Linux/Mac используйте iptables/ufw")

        except Exception as e:
            if output_text:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")
            self.log(f"Ошибка закрытия порта: {e}", 'ERROR')

    # ==================== СЕТЕВЫЕ ИНСТРУМЕНТЫ ====================

    def ping_tool(self):
        """Инструмент ping"""
        dialog = tk.Toplevel()
        dialog.title("Ping инструмент")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Ping инструмент", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        host_frame = ttk.Frame(main_frame)
        host_frame.pack(fill=tk.X, pady=5)

        ttk.Label(host_frame, text="Хост/IP:").pack(side=tk.LEFT, padx=5)
        host_entry = ttk.Entry(host_frame, width=30)
        host_entry.pack(side=tk.LEFT, padx=5)
        if self.main_app and hasattr(self.main_app, 'host_var'):
            host_entry.insert(0, self.main_app.host_var.get())

        count_frame = ttk.Frame(main_frame)
        count_frame.pack(fill=tk.X, pady=5)

        ttk.Label(count_frame, text="Количество пакетов:").pack(side=tk.LEFT, padx=5)
        count_var = tk.StringVar(value="4")
        count_combo = ttk.Combobox(count_frame, textvariable=count_var,
                                   values=["1", "2", "4", "8", "16"], width=10, state='readonly')
        count_combo.pack(side=tk.LEFT, padx=5)

        size_frame = ttk.Frame(main_frame)
        size_frame.pack(fill=tk.X, pady=5)

        ttk.Label(size_frame, text="Размер пакета (байт):").pack(side=tk.LEFT, padx=5)
        size_var = tk.StringVar(value="32")
        size_combo = ttk.Combobox(size_frame, textvariable=size_var,
                                  values=["32", "64", "128", "256", "512", "1024"], width=10, state='readonly')
        size_combo.pack(side=tk.LEFT, padx=5)

        timeout_frame = ttk.Frame(main_frame)
        timeout_frame.pack(fill=tk.X, pady=5)

        ttk.Label(timeout_frame, text="Таймаут (сек):").pack(side=tk.LEFT, padx=5)
        timeout_var = tk.StringVar(value="2")
        timeout_combo = ttk.Combobox(timeout_frame, textvariable=timeout_var,
                                     values=["1", "2", "3", "5", "10"], width=10, state='readonly')
        timeout_combo.pack(side=tk.LEFT, padx=5)

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def do_ping():
            host = host_entry.get().strip()
            count = count_var.get()
            size = size_var.get()
            timeout = timeout_var.get()

            if not host:
                messagebox.showwarning("Внимание", "Введите хост или IP адрес")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Pinging {host} with {size} bytes of data...\n\n")

            try:
                if platform.system().lower() == "windows":
                    cmd = ['ping', '-n', count, '-l', size, '-w', str(int(timeout) * 1000), host]
                else:
                    cmd = ['ping', '-c', count, '-s', size, '-W', timeout, host]

                def ping_thread():
                    try:
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                   text=True, universal_newlines=True)

                        for line in iter(process.stdout.readline, ''):
                            dialog.after(0, lambda l=line: output_text.insert(tk.END, l))
                            dialog.after(0, lambda: output_text.see(tk.END))

                        process.stdout.close()
                        return_code = process.wait()

                        if return_code == 0:
                            dialog.after(0, lambda: output_text.insert(tk.END, "\n✓ Ping успешен\n"))
                        else:
                            dialog.after(0, lambda: output_text.insert(tk.END, "\n✗ Ping не удался\n"))

                    except Exception as e:
                        dialog.after(0, lambda: output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n"))

                    dialog.after(0, lambda: stop_btn.config(state='disabled'))
                    dialog.after(0, lambda: start_btn.config(state='normal'))

                thread = threading.Thread(target=ping_thread, daemon=True)
                thread.start()

                start_btn.config(state='disabled')

            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")
                self.log(f"Ошибка ping: {e}", 'ERROR')

        def stop_ping():
            output_text.insert(tk.END, "\n⏹ Ping остановлен пользователем\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        start_btn = ttk.Button(btn_frame, text="Выполнить ping", command=do_ping)
        start_btn.pack(side=tk.LEFT, padx=5)

        stop_btn = ttk.Button(btn_frame, text="Остановить", command=stop_ping)
        stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def traceroute_tool(self):
        """Инструмент traceroute"""
        dialog = tk.Toplevel()
        dialog.title("Traceroute")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Traceroute инструмент", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Хост/IP:").pack(pady=5)
        host_entry = ttk.Entry(main_frame, width=40)
        host_entry.pack(pady=5)
        host_entry.insert(0, "google.com")

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def do_traceroute():
            host = host_entry.get().strip()
            if not host:
                messagebox.showwarning("Внимание", "Введите хост")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Traceroute to {host}...\n\n")

            try:
                if platform.system().lower() == "windows":
                    cmd = ['tracert', '-h', '30', '-w', '1000', host]
                else:
                    cmd = ['traceroute', '-m', '30', '-w', '1', host]

                def trace_thread():
                    try:
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                   text=True, universal_newlines=True)

                        for line in iter(process.stdout.readline, ''):
                            dialog.after(0, lambda l=line: output_text.insert(tk.END, l))
                            dialog.after(0, lambda: output_text.see(tk.END))

                        process.stdout.close()
                        return_code = process.wait()

                        if return_code == 0:
                            dialog.after(0, lambda: output_text.insert(tk.END, "\n✓ Traceroute завершен\n"))
                        else:
                            dialog.after(0, lambda: output_text.insert(tk.END, "\n✗ Traceroute не удался\n"))

                    except FileNotFoundError:
                        dialog.after(0, lambda: output_text.insert(tk.END, "\n✗ Команда traceroute/tracert не найдена\n"
                                                                           "Установите traceroute для вашей ОС\n"))
                    except Exception as e:
                        dialog.after(0, lambda: output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n"))

                thread = threading.Thread(target=trace_thread, daemon=True)
                thread.start()

            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Выполнить traceroute", command=do_traceroute).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def dns_lookup_tool(self):
        """Инструмент DNS lookup"""
        dialog = tk.Toplevel()
        dialog.title("DNS Lookup")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="DNS Lookup инструмент", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Домен или IP:").pack(pady=5)
        host_entry = ttk.Entry(main_frame, width=40)
        host_entry.pack(pady=5)
        host_entry.insert(0, "google.com")

        ttk.Label(main_frame, text="Тип записи:").pack(pady=5)
        type_var = tk.StringVar(value="A")
        type_combo = ttk.Combobox(main_frame, textvariable=type_var,
                                  values=["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR"],
                                  state='readonly', width=15)
        type_combo.pack(pady=5)

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def do_dns_lookup():
            host = host_entry.get().strip()
            record_type = type_var.get()

            if not host:
                messagebox.showwarning("Внимание", "Введите домен или IP")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"DNS Lookup for {host} (Type: {record_type})...\n\n")

            try:
                import dns.resolver
                import dns.reversename

                def dns_thread():
                    try:
                        if record_type == "PTR":
                            rev_name = dns.reversename.from_address(host)
                            answers = dns.resolver.resolve(rev_name, "PTR")
                        else:
                            answers = dns.resolver.resolve(host, record_type)

                        for rdata in answers:
                            dialog.after(0, lambda rd=rdata: output_text.insert(tk.END, f"{rd}\n"))

                        dialog.after(0, lambda: output_text.insert(tk.END, f"\n✓ Найдено {len(answers)} записей\n"))

                    except dns.resolver.NoAnswer:
                        dialog.after(0, lambda: output_text.insert(tk.END, "✗ Нет записей такого типа\n"))
                    except dns.resolver.NXDOMAIN:
                        dialog.after(0, lambda: output_text.insert(tk.END, "✗ Домен не существует\n"))
                    except dns.resolver.Timeout:
                        dialog.after(0, lambda: output_text.insert(tk.END, "✗ Таймаут DNS запроса\n"))
                    except Exception as e:
                        dialog.after(0, lambda: output_text.insert(tk.END, f"✗ Ошибка: {e}\n"))

                thread = threading.Thread(target=dns_thread, daemon=True)
                thread.start()

            except ImportError:
                output_text.insert(tk.END, "✗ Установите dnspython: pip install dnspython\n")
            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Выполнить DNS lookup", command=do_dns_lookup).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def bandwidth_test(self):
        """Тест пропускной способности"""
        dialog = tk.Toplevel()
        dialog.title("Тест пропускной способности")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Тест пропускной способности", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Сервер для теста:").pack(pady=5)
        server_var = tk.StringVar(value="speedtest.net")
        server_combo = ttk.Combobox(main_frame, textvariable=server_var,
                                    values=["speedtest.net", "fast.com", "google.com", "yandex.ru"],
                                    state='readonly', width=30)
        server_combo.pack(pady=5)

        ttk.Label(main_frame, text="Размер теста (МБ):").pack(pady=5)
        size_var = tk.StringVar(value="10")
        size_combo = ttk.Combobox(main_frame, textvariable=size_var,
                                  values=["1", "5", "10", "20", "50", "100"],
                                  state='readonly', width=15)
        size_combo.pack(pady=5)

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        progress.pack(pady=5)

        def do_bandwidth_test():
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, "Запуск теста скорости...\n\n")

            progress.start()

            def test_thread():
                try:
                    import speedtest

                    dialog.after(0, lambda: output_text.insert(tk.END, "Инициализация теста скорости...\n"))

                    st = speedtest.Speedtest()
                    st.get_best_server()

                    dialog.after(0, lambda: output_text.insert(tk.END,
                                                               f"Сервер: {st.best['name']} ({st.best['country']})\n"))
                    dialog.after(0, lambda: output_text.insert(tk.END, f"Пинг: {st.best['latency']:.2f} ms\n\n"))

                    dialog.after(0, lambda: output_text.insert(tk.END, "Тест скорости загрузки...\n"))
                    download_speed = st.download() / 1_000_000
                    dialog.after(0, lambda: output_text.insert(tk.END, f"Скачивание: {download_speed:.2f} Mbps\n"))

                    dialog.after(0, lambda: output_text.insert(tk.END, "Тест скорости отдачи...\n"))
                    upload_speed = st.upload() / 1_000_000
                    dialog.after(0, lambda: output_text.insert(tk.END, f"Отдача: {upload_speed:.2f} Mbps\n\n"))

                    dialog.after(0, lambda: output_text.insert(tk.END, f"Итоговая скорость:\n"))
                    dialog.after(0, lambda: output_text.insert(tk.END, f"  ↓ Скачивание: {download_speed:.2f} Mbps\n"))
                    dialog.after(0, lambda: output_text.insert(tk.END, f"  ↑ Отдача: {upload_speed:.2f} Mbps\n"))

                    if download_speed > 100:
                        dialog.after(0, lambda: output_text.insert(tk.END, "\n✓ Отличная скорость интернета!\n"))
                    elif download_speed > 50:
                        dialog.after(0, lambda: output_text.insert(tk.END, "\n✓ Хорошая скорость интернета\n"))
                    elif download_speed > 10:
                        dialog.after(0, lambda: output_text.insert(tk.END, "\n✓ Средняя скорость интернета\n"))
                    else:
                        dialog.after(0, lambda: output_text.insert(tk.END, "\n⚠ Медленная скорость интернета\n"))

                except ImportError:
                    dialog.after(0, lambda: output_text.insert(tk.END,
                                                               "\n✗ Установите speedtest-cli: pip install speedtest-cli\n"))
                except Exception as e:
                    dialog.after(0, lambda: output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n"))

                finally:
                    dialog.after(0, lambda: progress.stop())

            thread = threading.Thread(target=test_thread, daemon=True)
            thread.start()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Начать тест", command=do_bandwidth_test).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def firewall_check(self):
        """Проверка брандмауэра"""
        dialog = tk.Toplevel()
        dialog.title("Проверка брандмауэра")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Проверка брандмауэра", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        output_text = scrolledtext.ScrolledText(main_frame, height=20)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def check_firewall():
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, "Проверка настроек брандмауэра...\n\n")

            try:
                if platform.system() == "Windows":
                    cmd = ['netsh', 'advfirewall', 'show', 'allprofiles']
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                    output_text.insert(tk.END, "=== Статус брандмауэра Windows ===\n\n")
                    output_text.insert(tk.END, result.stdout)

                    output_text.insert(tk.END, "\n=== Открытые порты ===\n\n")
                    cmd_ports = ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=all']
                    result_ports = subprocess.run(cmd_ports, capture_output=True, text=True, shell=True)

                    open_rules = []
                    lines = result_ports.stdout.split('\n')
                    for line in lines:
                        if 'Разрешить' in line or 'Allow' in line:
                            open_rules.append(line.strip())

                    if open_rules:
                        for rule in open_rules[:20]:
                            output_text.insert(tk.END, f"{rule}\n")
                        if len(open_rules) > 20:
                            output_text.insert(tk.END, f"... и еще {len(open_rules) - 20} правил\n")
                    else:
                        output_text.insert(tk.END, "Нет открытых правил\n")

                elif platform.system() == "Linux":
                    try:
                        cmd = ['sudo', 'iptables', '-L', '-n', '-v']
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        output_text.insert(tk.END, "=== iptables правила ===\n\n")
                        output_text.insert(tk.END, result.stdout)
                    except:
                        try:
                            cmd = ['sudo', 'ufw', 'status', 'verbose']
                            result = subprocess.run(cmd, capture_output=True, text=True)
                            output_text.insert(tk.END, "=== UFW статус ===\n\n")
                            output_text.insert(tk.END, result.stdout)
                        except:
                            output_text.insert(tk.END, "Не удалось проверить брандмауэр\n")

                else:
                    output_text.insert(tk.END, f"Проверка брандмауэра для {platform.system()} не реализована\n")

                output_text.insert(tk.END, "\n✓ Проверка завершена\n")

            except Exception as e:
                output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Проверить брандмауэр", command=check_firewall).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    # ==================== HTTP СЕРВЕР ====================

    def start_server_tool(self):
        """Запуск HTTP сервера"""
        dialog = tk.Toplevel()
        dialog.title("Запуск HTTP сервера")
        dialog.geometry("800x700")

        self.server_port = tk.StringVar(value="8080")
        self.server_html = ""
        self.server_css = ""
        self.server_js = ""

        ttk.Label(dialog, text="Настройка HTTP сервера", font=('Arial', 12)).pack(pady=10)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Настройки")

        port_frame = ttk.Frame(settings_frame)
        port_frame.pack(fill=tk.X, pady=10, padx=10)

        ttk.Label(port_frame, text="Порт сервера:").pack(side=tk.LEFT, padx=5)
        port_entry = ttk.Entry(port_frame, textvariable=self.server_port, width=10)
        port_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(port_frame, text="Проверить порт",
                   command=lambda: self.check_server_port(self.server_port.get())).pack(side=tk.LEFT, padx=10)

        info_frame = ttk.LabelFrame(settings_frame, text="Информация о доступе", padding="10")
        info_frame.pack(fill=tk.X, pady=10, padx=10)

        self.access_info = scrolledtext.ScrolledText(info_frame, height=6)
        self.access_info.pack(fill=tk.BOTH, expand=True)

        self.update_server_info()

        html_frame = ttk.Frame(notebook)
        notebook.add(html_frame, text="HTML")

        ttk.Label(html_frame, text="HTML код (будет внутри <body>):").pack(pady=5)

        self.html_editor = scrolledtext.ScrolledText(html_frame, height=15)
        self.html_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.html_editor.insert(tk.END, """<h1>Добро пожаловать на мой сервер!</h1>
<p>Это тестовая страница HTTP сервера.</p>
<button onclick="showMessage()">Нажми меня</button>
<div id="message" style="margin-top: 20px;"></div>""")

        css_frame = ttk.Frame(notebook)
        notebook.add(css_frame, text="CSS")

        ttk.Label(css_frame, text="CSS стили:").pack(pady=5)

        self.css_editor = scrolledtext.ScrolledText(css_frame, height=15)
        self.css_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.css_editor.insert(tk.END, """body {
    font-family: Arial, sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    background-color: #f0f0f0;
}
h1 {
    color: #333;
}
button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
}
button:hover {
    background-color: #45a049;
}""")

        js_frame = ttk.Frame(notebook)
        notebook.add(js_frame, text="JavaScript")

        ttk.Label(js_frame, text="JavaScript код:").pack(pady=5)

        self.js_editor = scrolledtext.ScrolledText(js_frame, height=15)
        self.js_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.js_editor.insert(tk.END, """function showMessage() {
    const messages = [
        "Привет от HTTP сервера!",
        "Сервер работает отлично!",
        "Вы можете изменить этот код",
        "Добавьте свой функционал"
    ];
    const randomMessage = messages[Math.floor(Math.random() * messages.length)];
    document.getElementById('message').innerHTML = '<strong>' + randomMessage + '</strong>';

    const messageDiv = document.getElementById('message');
    messageDiv.style.transition = 'all 0.3s';
    messageDiv.style.color = '#d35400';
    setTimeout(() => {
        messageDiv.style.color = '#333';
    }, 300);
}""")

        status_frame = ttk.Frame(dialog)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.server_status = ttk.Label(status_frame, text="Сервер не запущен", foreground="red")
        self.server_status.pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Запустить сервер",
                   command=self.start_http_server).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Остановить сервер",
                   command=self.stop_http_server).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Открыть в браузере",
                   command=self.open_server_in_browser).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть",
                   command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def update_server_info(self):
        """Обновление информации о доступе к серверу"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()

            port = self.server_port.get()

            info = f"Локальный доступ:\n"
            info += f"  http://localhost:{port}\n"
            info += f"  http://127.0.0.1:{port}\n\n"

            info += f"Доступ из локальной сети:\n"
            info += f"  http://{local_ip}:{port}\n\n"

            info += f"Для доступа с других устройств:\n"
            info += f"  • Убедитесь, что устройства в одной сети\n"
            info += f"  • Откройте порт {port} в брандмауэре\n"
            info += f"  • Используйте IP адрес: {local_ip}\n"

            self.access_info.delete(1.0, tk.END)
            self.access_info.insert(tk.END, info)

        except Exception as e:
            self.access_info.delete(1.0, tk.END)
            self.access_info.insert(tk.END, f"Ошибка получения информации: {e}")

    def check_server_port(self, port_str):
        """Проверка доступности порта"""
        try:
            port = int(port_str)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)

            result = sock.connect_ex(('localhost', port))
            sock.close()

            if result == 0:
                messagebox.showwarning("Порт занят",
                                       f"Порт {port} уже используется другим приложением.\n"
                                       f"Выберите другой порт или остановите приложение.")
            else:
                messagebox.showinfo("Порт свободен",
                                    f"Порт {port} доступен для использования.")

        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректный номер порта")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def start_http_server(self):
        """Запуск HTTP сервера"""
        try:
            port = int(self.server_port.get())

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            if sock.connect_ex(('localhost', port)) == 0:
                sock.close()
                messagebox.showerror("Ошибка", f"Порт {port} уже используется")
                return
            sock.close()

            html_code = self.html_editor.get(1.0, tk.END)
            css_code = self.css_editor.get(1.0, tk.END)
            js_code = self.js_editor.get(1.0, tk.END)

            class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html; charset=utf-8')
                        self.end_headers()

                        full_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTTP Сервер</title>
    <style>
    {css_code}
    </style>
</head>
<body>
    {html_code}
    <script>
    {js_code}
    </script>
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ccc; color: #666;">
        <p>Сервер запущен на порту {port}</p>
        <p>Локальное время: <span id="datetime"></span></p>
        <script>
        function updateDateTime() {{
            const now = new Date();
            document.getElementById('datetime').textContent = now.toLocaleString('ru-RU');
        }}
        updateDateTime();
        setInterval(updateDateTime, 1000);
        </script>
    </footer>
</body>
</html>"""

                        self.wfile.write(full_html.encode('utf-8'))
                    else:
                        super().do_GET()

            self.http_server = socketserver.TCPServer(("", port), CustomHTTPRequestHandler)
            self.server_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.server_thread.start()

            self.server_running = True
            self.server_status.config(text=f"Сервер запущен на порту {port}", foreground="green")

            self.log(f"HTTP сервер запущен на порту {port}", 'INFO')
            messagebox.showinfo("Сервер запущен",
                                f"HTTP сервер запущен на порту {port}\n\n"
                                f"Доступ по адресам:\n"
                                f"• http://localhost:{port}\n"
                                f"• http://127.0.0.1:{port}")

        except Exception as e:
            self.log(f"Ошибка запуска сервера: {e}", 'ERROR')
            messagebox.showerror("Ошибка", str(e))

    def stop_http_server(self):
        """Остановка HTTP сервера"""
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
            self.http_server = None
            self.server_thread = None
            self.server_running = False

            self.server_status.config(text="Сервер не запущен", foreground="red")
            self.log("HTTP сервер остановлен", 'INFO')
            messagebox.showinfo("Сервер остановлен", "HTTP сервер был остановлен")

    def open_server_in_browser(self):
        """Открытие сервера в браузере"""
        if self.server_running:
            port = self.server_port.get()
            url = f"http://localhost:{port}"
            webbrowser.open(url)
            self.log(f"Открыт {url}", 'INFO')
        else:
            messagebox.showwarning("Сервер не запущен", "Сначала запустите сервер")

    # ==================== ДРУГИЕ ИНСТРУМЕНТЫ ====================

    def network_monitor(self):
        """Монитор сети"""
        dialog = tk.Toplevel()
        dialog.title("Монитор сети")
        dialog.geometry("700x600")

        ttk.Label(dialog, text="Монитор сетевой активности", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        info_frame = ttk.LabelFrame(main_frame, text="Текущие соединения", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True)

        self.connections_text = scrolledtext.ScrolledText(info_frame, height=20)
        self.connections_text.pack(fill=tk.BOTH, expand=True)

        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=10)

        self.stats_label = ttk.Label(stats_frame, text="Нажмите 'Обновить' для показа статистики")
        self.stats_label.pack()

        def update_network_info():
            try:
                self.connections_text.delete(1.0, tk.END)

                if platform.system() == "Windows":
                    cmd = ['netstat', '-an']
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                    self.connections_text.insert(tk.END, "=== Сетевые соединения ===\n\n")
                    self.connections_text.insert(tk.END, result.stdout)

                    lines = result.stdout.split('\n')
                    tcp_count = sum(1 for line in lines if 'TCP' in line)
                    udp_count = sum(1 for line in lines if 'UDP' in line)
                    listening_count = sum(1 for line in lines if 'LISTENING' in line)

                    self.stats_label.config(
                        text=f"TCP: {tcp_count} | UDP: {udp_count} | Listening: {listening_count}"
                    )

                else:
                    cmd = ['netstat', '-tulpn']
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                    self.connections_text.insert(tk.END, "=== Сетевые соединения ===\n\n")
                    self.connections_text.insert(tk.END, result.stdout)

            except Exception as e:
                self.connections_text.insert(tk.END, f"Ошибка: {e}\n")

        def start_monitoring():
            def monitoring_thread():
                while monitoring_active[0]:
                    dialog.after(0, update_network_info)
                    time.sleep(5)

            monitoring_active[0] = True
            thread = threading.Thread(target=monitoring_thread, daemon=True)
            thread.start()
            start_btn.config(state='disabled')
            stop_btn.config(state='normal')

        def stop_monitoring():
            monitoring_active[0] = False
            start_btn.config(state='normal')
            stop_btn.config(state='disabled')

        monitoring_active = [False]

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        start_btn = ttk.Button(btn_frame, text="Начать мониторинг", command=start_monitoring)
        start_btn.pack(side=tk.LEFT, padx=5)

        stop_btn = ttk.Button(btn_frame, text="Остановить мониторинг", command=stop_monitoring, state='disabled')
        stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Обновить", command=update_network_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Экспорт",
                   command=lambda: self.export_text(self.connections_text.get(1.0, tk.END))).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def quick_scan(self):
        """Быстрое сканирование"""
        if self.main_app and hasattr(self.main_app, 'set_port_range'):
            self.main_app.set_port_range((1, 1000))
            if hasattr(self.main_app, 'start_scan'):
                self.main_app.start_scan()

    def targeted_scan(self):
        """Целевое сканирование"""
        dialog = tk.Toplevel()
        dialog.title("Целевое сканирование")
        dialog.geometry("400x300")

        ttk.Label(dialog, text="Выберите тип сканирования:").pack(pady=20)

        options = [
            ("Веб-серверы (80,443,8080,8443)", [80, 443, 8080, 8443]),
            ("Базы данных (3306,5432,27017)", [3306, 5432, 27017, 6379]),
            ("Игровые серверы", [25565, 27015, 27016, 7777]),
            ("Принтеры/Сети (515,9100)", [515, 9100, 631]),
            ("Удаленное управление (3389,5900)", [3389, 5900, 5800])
        ]

        for text, ports in options:
            btn = ttk.Button(dialog, text=text,
                             command=lambda p=ports: self.do_targeted_scan(p, dialog))
            btn.pack(pady=5)

    def do_targeted_scan(self, ports, dialog):
        """Выполнить целевое сканирование"""
        dialog.destroy()
        if self.main_app and hasattr(self.main_app, 'set_port_range'):
            self.main_app.set_port_range((min(ports), max(ports)))
            if hasattr(self.main_app, 'start_scan'):
                self.main_app.start_scan()

    def traffic_analysis(self):
        """Анализ трафика"""
        dialog = tk.Toplevel()
        dialog.title("Анализ трафика")
        dialog.geometry("700x500")

        ttk.Label(dialog, text="Анализ сетевого трафика", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        output_text = scrolledtext.ScrolledText(main_frame, height=20)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def analyze_traffic():
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, "Анализ сетевого трафика...\n\n")

            try:
                if platform.system() == "Windows":
                    cmd = ['netstat', '-e']
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                    output_text.insert(tk.END, "=== Статистика сетевого интерфейса ===\n\n")
                    output_text.insert(tk.END, result.stdout)

                    output_text.insert(tk.END, "\n=== Процессы использующие сеть ===\n\n")
                    cmd2 = ['netstat', '-b', '-o']
                    try:
                        result2 = subprocess.run(cmd2, capture_output=True, text=True, shell=True)
                        lines = result2.stdout.split('\n')[:50]
                        output_text.insert(tk.END, '\n'.join(lines))
                    except:
                        output_text.insert(tk.END, "Требуются права администратора\n")

                else:
                    cmd = ['ifconfig']
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                    output_text.insert(tk.END, "=== Статистика сетевых интерфейсов ===\n\n")
                    output_text.insert(tk.END, result.stdout)

                    output_text.insert(tk.END, "\n=== TOP процессов по сети ===\n\n")
                    try:
                        cmd2 = ['nethogs', '-v', '3']
                        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=5)
                        output_text.insert(tk.END, result2.stdout)
                    except:
                        output_text.insert(tk.END, "Установите nethogs: sudo apt install nethogs\n")

                output_text.insert(tk.END, "\n✓ Анализ завершен\n")

            except Exception as e:
                output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Анализировать трафик", command=analyze_traffic).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def network_setup(self):
        """Настройка сети"""
        dialog = tk.Toplevel()
        dialog.title("Настройка сети")
        dialog.geometry("500x400")

        ttk.Label(dialog, text="Настройка сетевых параметров", font=('Arial', 12)).pack(pady=10)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        dns_frame = ttk.Frame(notebook)
        notebook.add(dns_frame, text="DNS")

        ttk.Label(dns_frame, text="Предпочитаемый DNS сервер:").pack(pady=5)
        dns1_entry = ttk.Entry(dns_frame, width=20)
        dns1_entry.pack(pady=5)
        dns1_entry.insert(0, "8.8.8.8")

        ttk.Label(dns_frame, text="Альтернативный DNS сервер:").pack(pady=5)
        dns2_entry = ttk.Entry(dns_frame, width=20)
        dns2_entry.pack(pady=5)
        dns2_entry.insert(0, "8.8.4.4")

        output_text = scrolledtext.ScrolledText(dns_frame, height=10)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def set_dns():
            dns1 = dns1_entry.get()
            dns2 = dns2_entry.get()

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Настройка DNS: {dns1}, {dns2}\n\n")

            try:
                if platform.system() == "Windows":
                    interfaces = subprocess.run(['netsh', 'interface', 'show', 'interface'],
                                                capture_output=True, text=True, shell=True)

                    lines = interfaces.stdout.split('\n')
                    for line in lines:
                        if 'Подключено' in line or 'Connected' in line:
                            parts = line.split()
                            if len(parts) > 3:
                                interface_name = ' '.join(parts[3:])

                                cmd = ['netsh', 'interface', 'ipv4', 'set', 'dns',
                                       f'name="{interface_name}"', 'static', dns1, 'primary']
                                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                                if result.returncode == 0:
                                    output_text.insert(tk.END, f"✓ Основной DNS установлен для {interface_name}\n")

                                    if dns2:
                                        cmd2 = ['netsh', 'interface', 'ipv4', 'add', 'dns',
                                                f'name="{interface_name}"', dns2, 'index=2']
                                        subprocess.run(cmd2, capture_output=True, text=True, shell=True)
                                        output_text.insert(tk.END, f"✓ Альтернативный DNS установлен\n")
                                else:
                                    output_text.insert(tk.END, f"✗ Ошибка: {result.stderr}\n")

                    output_text.insert(tk.END, "\n⚠ Может потребоваться перезагрузка\n")

                else:
                    output_text.insert(tk.END, "Для Linux/Mac измените /etc/resolv.conf\n")

            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

        ttk.Button(dns_frame, text="Установить DNS", command=set_dns).pack(pady=10)

        hosts_frame = ttk.Frame(notebook)
        notebook.add(hosts_frame, text="Hosts файл")

        hosts_text = scrolledtext.ScrolledText(hosts_frame, height=15)
        hosts_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        try:
            hosts_path = r'C:\Windows\System32\drivers\etc\hosts' if platform.system() == "Windows" else '/etc/hosts'
            with open(hosts_path, 'r', encoding='utf-8') as f:
                hosts_text.insert(tk.END, f.read())
        except:
            hosts_text.insert(tk.END, "Не удалось загрузить hosts файл\n")

        def save_hosts():
            try:
                hosts_path = r'C:\Windows\System32\drivers\etc\hosts' if platform.system() == "Windows" else '/etc/hosts'
                content = hosts_text.get(1.0, tk.END)

                if platform.system() == "Windows":
                    import ctypes
                    if not ctypes.windll.shell32.IsUserAnAdmin():
                        messagebox.showwarning("Требуются права", "Запустите программу от имени администратора")
                        return

                with open(hosts_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                messagebox.showinfo("Успех", "Hosts файл сохранен")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        ttk.Button(hosts_frame, text="Сохранить hosts", command=save_hosts).pack(pady=10)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack()

    def ssl_check(self):
        """Проверка SSL сертификата"""
        dialog = tk.Toplevel()
        dialog.title("Проверка SSL")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Проверка SSL сертификата", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Домен (например: google.com):").pack(pady=5)
        domain_entry = ttk.Entry(main_frame, width=40)
        domain_entry.pack(pady=5)
        domain_entry.insert(0, "google.com")

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def check_ssl():
            domain = domain_entry.get().strip()
            if not domain:
                messagebox.showwarning("Внимание", "Введите домен")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Проверка SSL для {domain}...\n\n")

            try:
                import ssl
                import certifi
                from datetime import datetime

                context = ssl.create_default_context(cafile=certifi.where())

                with socket.create_connection((domain, 443)) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()

                        output_text.insert(tk.END, "=== Информация о SSL сертификате ===\n\n")

                        subject = dict(x[0] for x in cert['subject'])
                        output_text.insert(tk.END, "Субъект:\n")
                        for key, value in subject.items():
                            output_text.insert(tk.END, f"  {key}: {value}\n")

                        output_text.insert(tk.END, "\nИздатель:\n")
                        issuer = dict(x[0] for x in cert['issuer'])
                        for key, value in issuer.items():
                            output_text.insert(tk.END, f"  {key}: {value}\n")

                        output_text.insert(tk.END, "\nСрок действия:\n")
                        not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                        not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                        output_text.insert(tk.END, f"  Начало: {not_before}\n")
                        output_text.insert(tk.END, f"  Окончание: {not_after}\n")

                        now = datetime.now()
                        days_left = (not_after - now).days

                        output_text.insert(tk.END, f"\nОсталось дней: {days_left}\n")

                        if days_left > 30:
                            output_text.insert(tk.END, "\n✓ Сертификат действителен\n")
                        elif days_left > 0:
                            output_text.insert(tk.END, f"\n⚠ Сертификат истекает через {days_left} дней\n")
                        else:
                            output_text.insert(tk.END, "\n✗ Сертификат просрочен\n")

                        output_text.insert(tk.END, f"\nВерсия: {cert.get('version', 'N/A')}\n")
                        output_text.insert(tk.END, f"Серийный номер: {cert.get('serialNumber', 'N/A')}\n")

            except Exception as e:
                output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Проверить SSL", command=check_ssl).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def whois_lookup(self):
        """WHOIS запрос"""
        dialog = tk.Toplevel()
        dialog.title("WHOIS Lookup")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="WHOIS Lookup", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Домен или IP:").pack(pady=5)
        query_entry = ttk.Entry(main_frame, width=40)
        query_entry.pack(pady=5)
        query_entry.insert(0, "google.com")

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def do_whois():
            query = query_entry.get().strip()
            if not query:
                messagebox.showwarning("Внимание", "Введите домен или IP")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"WHOIS запрос для {query}...\n\n")

            try:
                import whois

                domain_info = whois.whois(query)

                output_text.insert(tk.END, "=== WHOIS информация ===\n\n")

                if hasattr(domain_info, 'domain_name'):
                    output_text.insert(tk.END, f"Домен: {domain_info.domain_name}\n")

                if hasattr(domain_info, 'registrar'):
                    output_text.insert(tk.END, f"Регистратор: {domain_info.registrar}\n")

                if hasattr(domain_info, 'creation_date'):
                    output_text.insert(tk.END, f"Дата создания: {domain_info.creation_date}\n")

                if hasattr(domain_info, 'expiration_date'):
                    output_text.insert(tk.END, f"Дата истечения: {domain_info.expiration_date}\n")

                if hasattr(domain_info, 'updated_date'):
                    output_text.insert(tk.END, f"Дата обновления: {domain_info.updated_date}\n")

                if hasattr(domain_info, 'name_servers'):
                    output_text.insert(tk.END, f"\nDNS серверы:\n")
                    for ns in domain_info.name_servers:
                        output_text.insert(tk.END, f"  {ns}\n")

                if hasattr(domain_info, 'status'):
                    output_text.insert(tk.END, f"\nСтатус: {domain_info.status}\n")

                if hasattr(domain_info, 'emails'):
                    output_text.insert(tk.END, f"\nEmail контакты:\n")
                    for email in domain_info.emails:
                        output_text.insert(tk.END, f"  {email}\n")

                output_text.insert(tk.END, "\n✓ WHOIS запрос завершен\n")

            except ImportError:
                output_text.insert(tk.END, "✗ Установите python-whois: pip install python-whois\n")
            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Выполнить WHOIS", command=do_whois).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def export_text(self, text):
        """Экспорт текста в файл"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)

                messagebox.showinfo("Успех", "Текст экспортирован")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # Добавляем в конец класса ScannerTools:
    ScannerTools.network_mapper = AdvancedScannerTools.network_mapper
    ScannerTools.vulnerability_scanner = AdvancedScannerTools.vulnerability_scanner
    ScannerTools.packet_sniffer = AdvancedScannerTools.packet_sniffer
    ScannerTools.port_forwarding_tool = AdvancedScannerTools.port_forwarding_tool
    ScannerTools.subdomain_scanner = AdvancedScannerTools.subdomain_scanner
    ScannerTools.wifi_scanner = AdvancedScannerTools.wifi_scanner
    ScannerTools.password_cracker_tool = AdvancedScannerTools.password_cracker_tool