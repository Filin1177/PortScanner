import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from queue import Queue
import time


class PortScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Сканер открытых портов")
        self.root.geometry("700x500")

        self.queue = Queue()
        self.scanning = False
        self.scan_thread = None

        self.setup_gui()
        self.check_queue()

    def setup_gui(self):
        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = ttk.Label(main_frame, text="🔍 Сканер открытых портов",
                                font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))

        # Фрейм для настроек
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки сканирования", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Хост
        host_frame = ttk.Frame(settings_frame)
        host_frame.pack(fill=tk.X, pady=5)
        ttk.Label(host_frame, text="Хост/IP:", width=15).pack(side=tk.LEFT)
        self.host_entry = ttk.Entry(host_frame)
        self.host_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.host_entry.insert(0, "127.0.0.1")

        # Порты
        ports_frame = ttk.Frame(settings_frame)
        ports_frame.pack(fill=tk.X, pady=5)
        ttk.Label(ports_frame, text="Порты:", width=15).pack(side=tk.LEFT)

        ports_subframe = ttk.Frame(ports_frame)
        ports_subframe.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(ports_subframe, text="от").pack(side=tk.LEFT)
        self.start_port = ttk.Spinbox(ports_subframe, from_=1, to=65535, width=10)
        self.start_port.pack(side=tk.LEFT, padx=5)
        self.start_port.delete(0, tk.END)
        self.start_port.insert(0, "1")

        ttk.Label(ports_subframe, text="до").pack(side=tk.LEFT, padx=(10, 5))
        self.end_port = ttk.Spinbox(ports_subframe, from_=1, to=65535, width=10)
        self.end_port.pack(side=tk.LEFT, padx=(0, 5))
        self.end_port.delete(0, tk.END)
        self.end_port.insert(0, "1000")

        # Предустановленные диапазоны
        presets_frame = ttk.Frame(settings_frame)
        presets_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(presets_frame, text="Быстрый выбор:").pack(side=tk.LEFT)

        def set_wellknown():
            self.start_port.delete(0, tk.END)
            self.start_port.insert(0, "1")
            self.end_port.delete(0, tk.END)
            self.end_port.insert(0, "1024")

        def set_all():
            self.start_port.delete(0, tk.END)
            self.start_port.insert(0, "1")
            self.end_port.delete(0, tk.END)
            self.end_port.insert(0, "65535")

        ttk.Button(presets_frame, text="Well-known (1-1024)",
                   command=set_wellknown, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(presets_frame, text="Все порты (1-65535)",
                   command=set_all, width=15).pack(side=tk.LEFT)

        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.scan_button = ttk.Button(button_frame, text="▶ Начать сканирование",
                                      command=self.start_scan)
        self.scan_button.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_button = ttk.Button(button_frame, text="⏹ Остановить",
                                      command=self.stop_scan, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="🧹 Очистить",
                   command=self.clear_results).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="💾 Сохранить",
                   command=self.save_results).pack(side=tk.LEFT, padx=5)

        # Прогресс
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 5))

        # Статус
        self.status_label = ttk.Label(main_frame, text="✅ Готов к сканированию")
        self.status_label.pack(fill=tk.X)

        # Результаты
        results_frame = ttk.LabelFrame(main_frame, text="Результаты", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD)
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # Настройка цвета текста
        self.results_text.tag_config("open", foreground="#2E7D32", font=('Arial', 9, 'bold'))
        self.results_text.tag_config("closed", foreground="#757575")
        self.results_text.tag_config("error", foreground="#D84315")
        self.results_text.tag_config("header", foreground="#1565C0", font=('Arial', 10, 'bold'))

        # Статистика
        self.stats_label = ttk.Label(main_frame, text="")
        self.stats_label.pack(fill=tk.X)

        # Информация
        info_label = ttk.Label(main_frame,
                               text="💡 Совет: Для сканирования удаленных хостов убедитесь, что у вас есть разрешение",
                               foreground="#666", font=('Arial', 8))
        info_label.pack(fill=tk.X, pady=(5, 0))

    def check_port(self, host, port):
        """Проверяет один порт"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)  # Уменьшили таймаут
                result = sock.connect_ex((host, port))

                if result == 0:
                    try:
                        service = socket.getservbyport(port)
                    except:
                        service = "Неизвестная служба"

                    # Определяем известные службы
                    common_services = {
                        80: "HTTP", 443: "HTTPS", 21: "FTP", 22: "SSH",
                        23: "Telnet", 25: "SMTP", 53: "DNS", 110: "POP3",
                        143: "IMAP", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
                        27017: "MongoDB", 6379: "Redis", 8080: "HTTP-Proxy"
                    }

                    if port in common_services:
                        service = common_services[port]

                    return port, True, service
                else:
                    return port, False, None

        except socket.timeout:
            return port, False, "Таймаут"
        except Exception as e:
            return port, False, f"Ошибка: {str(e)[:30]}"

    def scan_ports(self, host, start_port, end_port):
        """Основная функция сканирования"""
        try:
            self.queue.put(("status", f"🔍 Сканируем {host} (порты {start_port}-{end_port})..."))

            open_ports = []
            total_ports = end_port - start_port + 1
            scanned = 0

            # Максимум 200 одновременных потоков
            max_threads = 200
            current_threads = []

            for port in range(start_port, end_port + 1):
                if not self.scanning:
                    break

                # Если достигли лимита потоков, ждем
                while len(current_threads) >= max_threads and self.scanning:
                    time.sleep(0.01)
                    # Убираем завершенные потоки
                    current_threads = [t for t in current_threads if t.is_alive()]

                thread = threading.Thread(target=self.process_port,
                                          args=(host, port, open_ports))
                thread.start()
                current_threads.append(thread)

                scanned += 1
                progress = (scanned / total_ports) * 100
                self.queue.put(("progress", progress))

            # Ждем завершения всех потоков
            for thread in current_threads:
                thread.join()

            if self.scanning:
                self.queue.put(("stats", f"✅ Сканирование завершено! Найдено открытых портов: {len(open_ports)}"))
                if open_ports:
                    self.queue.put(("result", "header", "\n📋 ОТКРЫТЫЕ ПОРТЫ:"))
                    for port in sorted(open_ports):
                        self.queue.put(("result", "open", f"   Порт {port} открыт"))

        except Exception as e:
            self.queue.put(("error", f"❌ Критическая ошибка: {str(e)}"))
        finally:
            self.queue.put(("scan_complete", None))

    def process_port(self, host, port, open_ports):
        """Обрабатывает результат сканирования порта"""
        if not self.scanning:
            return

        port_result, is_open, service = self.check_port(host, port)

        if is_open:
            message = f"🟢 Порт {port}: открыт ({service})"
            self.queue.put(("result", "open", message))
            open_ports.append(port)
        else:
            # Показываем только открытые порты или ошибки
            if service and "Ошибка" in service:
                message = f"🟠 Порт {port}: {service}"
                self.queue.put(("result", "error", message))
            # Закрытые порты не показываем, чтобы не засорять вывод

    def start_scan(self):
        """Запуск сканирования"""
        try:
            host = self.host_entry.get().strip()
            if not host:
                messagebox.showwarning("Внимание", "Введите хост или IP адрес")
                return

            try:
                start_port = int(self.start_port.get())
                end_port = int(self.end_port.get())

                if not (1 <= start_port <= 65535 and 1 <= end_port <= 65535):
                    messagebox.showwarning("Внимание", "Порт должен быть в диапазоне 1-65535")
                    return
                if start_port > end_port:
                    messagebox.showwarning("Внимание", "Начальный порт должен быть меньше конечного")
                    return

                # Предупреждение при большом диапазоне
                if (end_port - start_port) > 10000:
                    if not messagebox.askyesno("Подтверждение",
                                               f"Вы собираетесь сканировать {end_port - start_port + 1} портов.\n"
                                               "Это может занять много времени. Продолжить?"):
                        return

            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректные номера портов")
                return

            # Очищаем предыдущие результаты
            self.results_text.delete(1.0, tk.END)
            self.stats_label.config(text="")

            # Устанавливаем флаг сканирования
            self.scanning = True

            # Меняем состояние кнопок
            self.scan_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

            # Запускаем прогресс бар
            self.progress.start(10)

            # Запускаем сканирование в отдельном потоке
            self.scan_thread = threading.Thread(target=self.scan_ports,
                                                args=(host, start_port, end_port),
                                                daemon=True)
            self.scan_thread.start()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка запуска: {str(e)}")

    def stop_scan(self):
        """Остановка сканирования"""
        self.scanning = False
        self.status_label.config(text="⏹ Сканирование остановлено")
        self.progress.stop()

    def clear_results(self):
        """Очистка результатов"""
        self.results_text.delete(1.0, tk.END)
        self.stats_label.config(text="")
        self.status_label.config(text="✅ Готов к сканированию")

    def save_results(self):
        """Сохранение результатов в файл"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("Результаты сканирования портов\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(self.results_text.get(1.0, tk.END))

                messagebox.showinfo("Успех", f"Результаты сохранены в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {str(e)}")

    def check_queue(self):
        """Проверка очереди для обновления GUI"""
        try:
            while True:
                msg_type, *args = self.queue.get_nowait()

                if msg_type == "result":
                    tag, message = args
                    self.results_text.insert(tk.END, message + "\n", tag)
                    self.results_text.see(tk.END)

                elif msg_type == "status":
                    self.status_label.config(text=args[0])

                elif msg_type == "progress":
                    # Можно добавить determinate progress bar при желании
                    pass

                elif msg_type == "stats":
                    self.stats_label.config(text=args[0])
                    self.results_text.insert(tk.END, "\n" + args[0] + "\n", "header")

                elif msg_type == "error":
                    messagebox.showerror("Ошибка", args[0])

                elif msg_type == "scan_complete":
                    self.scan_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                    self.progress.stop()

        except:
            pass

        self.root.after(100, self.check_queue)


def main():
    root = tk.Tk()

    # Улучшаем внешний вид
    try:
        root.tk.call('tk', 'scaling', 1.5)  # Для высокого DPI
    except:
        pass

    # Центрируем окно
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{700}x{500}+{x}+{y}')

    app = PortScannerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()