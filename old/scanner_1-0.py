import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from queue import Queue


class PortScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Сканер открытых портов")
        self.root.geometry("700x500")

        # Очередь для безопасного обновления GUI из потоков
        self.queue = Queue()

        # Создание GUI
        self.setup_gui()

        # Запуск проверки очереди
        self.check_queue()

    def setup_gui(self):
        # Создаем стиль
        style = ttk.Style()
        style.theme_use('clam')

        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Настройка растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Заголовок
        title_label = ttk.Label(main_frame, text="Сканер открытых портов",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Ввод хоста
        ttk.Label(main_frame, text="Хост/IP:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.host_entry = ttk.Entry(main_frame, width=30)
        self.host_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.host_entry.insert(0, "localhost")

        # Диапазон портов
        ttk.Label(main_frame, text="Диапазон портов:").grid(row=2, column=0, sticky=tk.W, pady=5)

        ports_frame = ttk.Frame(main_frame)
        ports_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)

        ttk.Label(ports_frame, text="от").grid(row=0, column=0)
        self.start_port = ttk.Spinbox(ports_frame, from_=1, to=65535, width=8)
        self.start_port.grid(row=0, column=1, padx=5)
        self.start_port.delete(0, tk.END)
        self.start_port.insert(0, "1")

        ttk.Label(ports_frame, text="до").grid(row=0, column=2, padx=(10, 5))
        self.end_port = ttk.Spinbox(ports_frame, from_=1, to=65535, width=8)
        self.end_port.grid(row=0, column=3, padx=5)
        self.end_port.delete(0, tk.END)
        self.end_port.insert(0, "1024")

        # Кнопки сканирования
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)

        self.scan_button = ttk.Button(button_frame, text="Начать сканирование",
                                      command=self.start_scan)
        self.scan_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Остановить",
                                      command=self.stop_scan, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)

        ttk.Button(button_frame, text="Очистить",
                   command=self.clear_results).grid(row=0, column=2, padx=5)

        # Прогресс бар
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        # Статус
        self.status_label = ttk.Label(main_frame, text="Готов к сканированию")
        self.status_label.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # Результаты
        ttk.Label(main_frame, text="Результаты:").grid(row=6, column=0,
                                                       columnspan=2, sticky=tk.W)

        # Текстовое поле с прокруткой для результатов
        self.results_text = scrolledtext.ScrolledText(main_frame, height=15,
                                                      width=60, wrap=tk.WORD)
        self.results_text.grid(row=7, column=0, columnspan=2,
                               sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))

        # Настройка цвета текста
        self.results_text.tag_config("open", foreground="green")
        self.results_text.tag_config("closed", foreground="red")
        self.results_text.tag_config("error", foreground="orange")

        # Статистика
        self.stats_label = ttk.Label(main_frame, text="")
        self.stats_label.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        # Флаг для остановки сканирования
        self.scanning = False
        self.scan_thread = None

    def check_port(self, host, port, results, open_ports):
        """Проверяет один порт"""
        if not self.scanning:
            return

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))

            if result == 0:
                try:
                    service = socket.getservbyport(port)
                except:
                    service = "Неизвестная служба"

                message = f"Порт {port}: открыт ({service})"
                self.queue.put(("result", "open", message))
                open_ports.append(port)
            else:
                message = f"Порт {port}: закрыт"
                self.queue.put(("result", "closed", message))

            sock.close()

        except Exception as e:
            message = f"Порт {port}: ошибка - {str(e)}"
            self.queue.put(("result", "error", message))

    def scan_ports(self, host, start_port, end_port):
        """Основная функция сканирования"""
        try:
            self.queue.put(("status", f"Сканирование {host}:{start_port}-{end_port}"))

            open_ports = []
            threads = []
            results = []

            # Создаем потоки для сканирования портов
            for port in range(start_port, end_port + 1):
                if not self.scanning:
                    break

                thread = threading.Thread(target=self.check_port,
                                          args=(host, port, results, open_ports))
                threads.append(thread)
                thread.start()

                # Ограничиваем количество одновременных потоков
                if len(threads) >= 100:  # Максимум 100 потоков одновременно
                    for t in threads:
                        t.join()
                    threads = []

                # Обновляем прогресс
                progress = ((port - start_port + 1) / (end_port - start_port + 1)) * 100
                self.queue.put(("progress", progress))

            # Ждем завершения оставшихся потоков
            for thread in threads:
                thread.join()

            # Выводим статистику
            if self.scanning:
                self.queue.put(("stats", f"Найдено открытых портов: {len(open_ports)}"))
                if open_ports:
                    self.queue.put(("result", "open", "\nОткрытые порты: " +
                                    ", ".join(map(str, sorted(open_ports)))))

            self.queue.put(("status", "Сканирование завершено"))

        except Exception as e:
            self.queue.put(("error", f"Ошибка: {str(e)}"))
        finally:
            self.queue.put(("scan_complete", None))

    def start_scan(self):
        """Запуск сканирования"""
        try:
            host = self.host_entry.get().strip()
            if not host:
                messagebox.showerror("Ошибка", "Введите хост или IP")
                return

            try:
                start_port = int(self.start_port.get())
                end_port = int(self.end_port.get())

                if start_port < 1 or end_port > 65535:
                    messagebox.showerror("Ошибка", "Порт должен быть в диапазоне 1-65535")
                    return
                if start_port > end_port:
                    messagebox.showerror("Ошибка", "Начальный порт должен быть меньше конечного")
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
            self.progress.start()

            # Запускаем сканирование в отдельном потоке
            self.scan_thread = threading.Thread(target=self.scan_ports,
                                                args=(host, start_port, end_port))
            self.scan_thread.start()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка запуска: {str(e)}")

    def stop_scan(self):
        """Остановка сканирования"""
        self.scanning = False
        self.status_label.config(text="Сканирование остановлено")
        self.progress.stop()

    def clear_results(self):
        """Очистка результатов"""
        self.results_text.delete(1.0, tk.END)
        self.stats_label.config(text="")
        self.status_label.config(text="Готов к сканированию")

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
                    # Для determinate режима
                    # self.progress['value'] = args[0]
                    pass

                elif msg_type == "stats":
                    self.stats_label.config(text=args[0])

                elif msg_type == "error":
                    messagebox.showerror("Ошибка", args[0])

                elif msg_type == "scan_complete":
                    self.scan_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                    self.progress.stop()

        except:
            pass

        # Продолжаем проверять очередь
        self.root.after(100, self.check_queue)


def main():
    root = tk.Tk()
    app = PortScannerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()