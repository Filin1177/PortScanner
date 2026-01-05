import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from queue import Queue, Empty
import json
import os
import time
import subprocess
import platform
import webbrowser
from datetime import datetime
from urllib.parse import urlparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress

# Импорт для мини-браузера
try:
    import tkinterweb

    HAS_TKINTERWEB = True
except ImportError:
    HAS_TKINTERWEB = False
    print("Для мини-браузера установите: pip install tkinterweb")


class MegaPortScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ MegaKNIGHT Port Scanner Pro")
        self.root.geometry("1400x800")

        # Иконка
        try:
            self.root.iconbitmap('scanner.ico')
        except:
            pass

        # Конфигурация
        self.config_file = "scanner_config.json"
        self.history_file = "scan_history.json"
        self.log_file = "scanner.log"

        # Очереди и флаги
        self.queue = Queue()
        self.scanning = False
        self.scan_thread = None
        self.current_scan = {}

        # История и логи
        self.scan_history = self.load_history()
        self.open_ports_history = {}

        # Стили
        self.setup_styles()

        # GUI
        self.setup_gui()

        # Загрузка конфигурации
        self.load_config()

        # Обновление GUI
        self.check_queue()
        self.update_network_info()

        # Автосохранение каждые 30 сек
        self.root.after(30000, self.auto_save)

    def setup_styles(self):
        """Настройка стилей"""
        self.style = ttk.Style()

        # Современная тема
        self.style.theme_use('clam')

        # Цвета
        self.colors = {
            'open': '#2E7D32',
            'closed': '#757575',
            'error': '#D84315',
            'warning': '#FF8F00',
            'info': '#1565C0',
            'success': '#388E3C'
        }

        # Стиль для вкладок
        self.style.configure('Custom.TNotebook.Tab',
                             padding=[20, 5],
                             font=('Segoe UI', 10))

    def setup_gui(self):
        """Создание интерфейса"""
        # Главный контейнер
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Верхняя панель
        self.create_top_panel(main_container)

        # Центральная область с вкладками
        self.create_center_area(main_container)

        # Нижняя панель
        self.create_bottom_panel(main_container)

    def create_top_panel(self, parent):
        """Верхняя панель с основными кнопками"""
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # Заголовок
        title = ttk.Label(top_frame,
                          text="⚡ MEGAKNIGHT PORT SCANNER PRO",
                          font=('Segoe UI', 16, 'bold'))
        title.pack(side=tk.LEFT, padx=(0, 20))

        # Кнопки управления
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.RIGHT)

        buttons = [
            ("▶ Старт", self.start_scan, 'success'),
            ("⏸ Пауза", self.pause_scan, 'warning'),
            ("⏹ Стоп", self.stop_scan, 'error'),
            ("🧹 Очистить", self.clear_results, 'info'),
            ("💾 Сохранить", self.save_results, 'success'),
            ("📊 Отчет", self.generate_report, 'info'),
            ("⚙️ Настройки", self.open_settings, 'warning')
        ]

        for text, cmd, color in buttons:
            btn = ttk.Button(btn_frame, text=text, command=cmd,
                             style=f'{color.capitalize()}.TButton')
            btn.pack(side=tk.LEFT, padx=2)
            setattr(self, f'btn_{text}', btn)

    def create_center_area(self, parent):
        """Центральная область с вкладками"""
        # Notebook для вкладок
        self.notebook = ttk.Notebook(parent, style='Custom.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Создаем вкладки
        self.tab_scan = ttk.Frame(self.notebook)
        self.tab_network = ttk.Frame(self.notebook)
        self.tab_browser = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_logs = ttk.Frame(self.notebook)
        self.tab_tools = ttk.Frame(self.notebook)

        # Добавляем вкладки
        self.notebook.add(self.tab_scan, text='📡 Сканирование')
        self.notebook.add(self.tab_network, text='🌐 Сеть')
        self.notebook.add(self.tab_browser, text='🌍 Браузер')
        self.notebook.add(self.tab_history, text='📊 История')
        self.notebook.add(self.tab_logs, text='📝 Логи')
        self.notebook.add(self.tab_tools, text='🛠 Инструменты')

        # Заполняем вкладки
        self.setup_scan_tab()
        self.setup_network_tab()
        self.setup_browser_tab()
        self.setup_history_tab()
        self.setup_logs_tab()
        self.setup_tools_tab()

    def setup_scan_tab(self):
        """Вкладка сканирования"""
        # Левая панель - настройки
        left_panel = ttk.LabelFrame(self.tab_scan, text="Настройки сканирования", padding="10")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        # Хост
        ttk.Label(left_panel, text="Цель:").grid(row=0, column=0, sticky=tk.W, pady=5)

        host_frame = ttk.Frame(left_panel)
        host_frame.grid(row=0, column=1, sticky=tk.EW, pady=5)

        self.host_var = tk.StringVar(value="localhost")
        self.host_combo = ttk.Combobox(host_frame, textvariable=self.host_var, width=25)
        self.host_combo.grid(row=0, column=0)
        self.host_combo['values'] = ['localhost', '127.0.0.1', '192.168.1.1', '192.168.0.1']

        ttk.Button(host_frame, text="Сеть", command=self.scan_network).grid(row=0, column=1, padx=5)

        # Диапазон портов
        ttk.Label(left_panel, text="Порты:").grid(row=1, column=0, sticky=tk.W, pady=5)

        port_frame = ttk.Frame(left_panel)
        port_frame.grid(row=1, column=1, sticky=tk.EW, pady=5)

        self.port_start = ttk.Spinbox(port_frame, from_=1, to=65535, width=8)
        self.port_start.grid(row=0, column=0)
        self.port_start.set(1)

        ttk.Label(port_frame, text="-").grid(row=0, column=1, padx=5)

        self.port_end = ttk.Spinbox(port_frame, from_=1, to=65535, width=8)
        self.port_end.grid(row=0, column=2)
        self.port_end.set(1024)

        # Быстрые пресеты
        presets_frame = ttk.LabelFrame(left_panel, text="Быстрые диапазоны", padding="5")
        presets_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=10)

        presets = [
            ("Well Known (1-1024)", (1, 1024)),
            ("Common (1-10000)", (1, 10000)),
            ("All Ports", (1, 65535)),
            ("Web Ports", (80, 443, 8080, 8443)),
            ("Game Ports", (27015, 27016, 25565)),
        ]

        for i, (name, ports) in enumerate(presets):
            btn = ttk.Button(presets_frame, text=name,
                             command=lambda p=ports: self.set_port_range(p))
            btn.grid(row=i // 2, column=i % 2, sticky=tk.EW, padx=2, pady=2)

        # Метод сканирования
        ttk.Label(left_panel, text="Метод:").grid(row=3, column=0, sticky=tk.W, pady=5)

        self.scan_method = ttk.Combobox(left_panel, values=[
            "Полное сканирование",
            "Быстрое сканирование",
            "Только известные порты",
            "Пинг + сканирование"
        ], state="readonly", width=25)
        self.scan_method.grid(row=3, column=1, sticky=tk.EW, pady=5)
        self.scan_method.set("Быстрое сканирование")

        # Таймаут
        ttk.Label(left_panel, text="Таймаут (сек):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.DoubleVar(value=1.0)
        self.timeout_scale = ttk.Scale(left_panel, from_=0.1, to=5.0,
                                       variable=self.timeout_var, orient=tk.HORIZONTAL)
        self.timeout_scale.grid(row=4, column=1, sticky=tk.EW, pady=5)

        # Потоки
        ttk.Label(left_panel, text="Потоки:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.threads_var = tk.IntVar(value=100)
        self.threads_spin = ttk.Spinbox(left_panel, from_=1, to=500,
                                        textvariable=self.threads_var, width=10)
        self.threads_spin.grid(row=5, column=1, sticky=tk.W, pady=5)

        # Дополнительные опции
        self.var_show_closed = tk.BooleanVar(value=False)
        self.var_show_errors = tk.BooleanVar(value=True)
        self.var_save_logs = tk.BooleanVar(value=True)
        self.var_auto_open = tk.BooleanVar(value=False)

        ttk.Checkbutton(left_panel, text="Показывать закрытые",
                        variable=self.var_show_closed).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Checkbutton(left_panel, text="Показывать ошибки",
                        variable=self.var_show_errors).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Checkbutton(left_panel, text="Авто-сохранение",
                        variable=self.var_save_logs).grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Checkbutton(left_panel, text="Авто-открытие веб",
                        variable=self.var_auto_open).grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Правая панель - результаты
        right_panel = ttk.Frame(self.tab_scan)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Панель результатов
        results_frame = ttk.LabelFrame(right_panel, text="Результаты сканирования", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview для результатов
        columns = ('port', 'status', 'service', 'banner', 'response')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=20)

        # Заголовки
        self.results_tree.heading('port', text='Порт')
        self.results_tree.heading('status', text='Статус')
        self.results_tree.heading('service', text='Служба')
        self.results_tree.heading('banner', text='Баннер')
        self.results_tree.heading('response', text='Ответ')

        # Колонки
        self.results_tree.column('port', width=80)
        self.results_tree.column('status', width=100)
        self.results_tree.column('service', width=150)
        self.results_tree.column('banner', width=200)
        self.results_tree.column('response', width=300)

        # Скроллбар
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)

        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Контекстное меню
        self.setup_context_menu()

        # Статистика
        stats_frame = ttk.Frame(right_panel)
        stats_frame.pack(fill=tk.X, pady=(5, 0))

        self.stats_label = ttk.Label(stats_frame, text="Готов к сканированию")
        self.stats_label.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(stats_frame, mode='indeterminate', length=300)
        self.progress.pack(side=tk.RIGHT, padx=10)

    def setup_network_tab(self):
        """Вкладка информации о сети"""
        # Информация о текущей сети
        info_frame = ttk.LabelFrame(self.tab_network, text="Сетевая информация", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Текстовое поле для информации
        self.network_info = scrolledtext.ScrolledText(info_frame, height=20)
        self.network_info.pack(fill=tk.BOTH, expand=True)

        # Кнопки обновления
        btn_frame = ttk.Frame(self.tab_network)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Обновить",
                   command=self.update_network_info).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Сканировать сеть",
                   command=self.scan_local_network).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Экспорт",
                   command=self.export_network_info).pack(side=tk.LEFT, padx=2)

    def setup_browser_tab(self):
        """Вкладка мини-браузера"""
        if HAS_TKINTERWEB:
            browser_frame = ttk.Frame(self.tab_browser)
            browser_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Панель управления
            control_frame = ttk.Frame(browser_frame)
            control_frame.pack(fill=tk.X, pady=(0, 5))

            self.browser_url = ttk.Entry(control_frame, width=50)
            self.browser_url.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            self.browser_url.insert(0, "http://localhost:8080")

            ttk.Button(control_frame, text="Перейти",
                       command=self.browser_go).pack(side=tk.LEFT, padx=2)
            ttk.Button(control_frame, text="Назад",
                       command=self.browser_back).pack(side=tk.LEFT, padx=2)
            ttk.Button(control_frame, text="Вперед",
                       command=self.browser_forward).pack(side=tk.LEFT, padx=2)
            ttk.Button(control_frame, text="Обновить",
                       command=self.browser_refresh).pack(side=tk.LEFT, padx=2)

            # Сам браузер
            self.html_frame = tkinterweb.HtmlFrame(browser_frame)
            self.html_frame.pack(fill=tk.BOTH, expand=True)
        else:
            # Заглушка если нет tkinterweb
            ttk.Label(self.tab_browser,
                      text="Установите tkinterweb: pip install tkinterweb\n"
                           "Для просмотра веб-интерфейсов портов",
                      justify=tk.CENTER).pack(expand=True)

            # Простой просмотрщик
            simple_frame = ttk.Frame(self.tab_browser)
            simple_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            ttk.Label(simple_frame, text="Быстрый переход к портам:").pack(pady=5)

            common_ports = [
                ("HTTP (80)", "http://{host}:80"),
                ("HTTPS (443)", "https://{host}:443"),
                ("Web Admin (8080)", "http://{host}:8080"),
                ("Router (192.168.1.1)", "http://192.168.1.1"),
                ("PHPMyAdmin (3306)", "http://{host}:3306"),
            ]

            for name, template in common_ports:
                btn = ttk.Button(simple_frame, text=name,
                                 command=lambda t=template: self.open_in_browser(t))
                btn.pack(pady=2)

    def setup_history_tab(self):
        """Вкладка истории"""
        history_frame = ttk.Frame(self.tab_history)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview для истории
        columns = ('date', 'target', 'ports', 'open', 'duration', 'method')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=20)

        # Заголовки
        self.history_tree.heading('date', text='Дата')
        self.history_tree.heading('target', text='Цель')
        self.history_tree.heading('ports', text='Порты')
        self.history_tree.heading('open', text='Открыто')
        self.history_tree.heading('duration', text='Время')
        self.history_tree.heading('method', text='Метод')

        # Колонки
        self.history_tree.column('date', width=150)
        self.history_tree.column('target', width=150)
        self.history_tree.column('ports', width=100)
        self.history_tree.column('open', width=80)
        self.history_tree.column('duration', width=80)
        self.history_tree.column('method', width=120)

        # Скроллбар
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопки управления историей
        btn_frame = ttk.Frame(self.tab_history)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Загрузить историю",
                   command=self.load_history_gui).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Очистить историю",
                   command=self.clear_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Повторить сканирование",
                   command=self.repeat_scan).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Экспорт в CSV",
                   command=self.export_history_csv).pack(side=tk.LEFT, padx=2)

    def setup_logs_tab(self):
        """Вкладка логов"""
        logs_frame = ttk.Frame(self.tab_logs)
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Текстовое поле для логов
        self.logs_text = scrolledtext.ScrolledText(logs_frame, height=30)
        self.logs_text.pack(fill=tk.BOTH, expand=True)

        # Панель управления логами
        control_frame = ttk.Frame(self.tab_logs)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(control_frame, text="Очистить логи",
                   command=self.clear_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Сохранить логи",
                   command=self.save_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Экспорт",
                   command=self.export_logs).pack(side=tk.LEFT, padx=2)

        # Уровень логирования
        ttk.Label(control_frame, text="Уровень:").pack(side=tk.LEFT, padx=(20, 5))
        self.log_level = ttk.Combobox(control_frame, values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                                      state='readonly', width=10)
        self.log_level.pack(side=tk.LEFT)
        self.log_level.set('INFO')

    def setup_tools_tab(self):
        """Вкладка инструментов"""
        tools_frame = ttk.Frame(self.tab_tools)
        tools_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Сетка для инструментов
        for i in range(3):
            tools_frame.columnconfigure(i, weight=1)
        for i in range(4):
            tools_frame.rowconfigure(i, weight=1)

        tools = [
            ("🔧 Открыть порт", self.open_port_tool, 0, 0),
            ("🔒 Закрыть порт", self.close_port_tool, 0, 1),
            ("📡 Ping хоста", self.ping_tool, 0, 2),
            ("🌐 Traceroute", self.traceroute_tool, 1, 0),
            ("🔍 DNS lookup", self.dns_lookup_tool, 1, 1),
            ("📊 Пропускная способность", self.bandwidth_test, 1, 2),
            ("🛡️ Проверка брандмауэра", self.firewall_check, 2, 0),
            ("🚀 Запустить сервер", self.start_server_tool, 2, 1),
            ("📶 Монитор сети", self.network_monitor, 2, 2),
            ("⚡ Быстрый скан", self.quick_scan, 3, 0),
            ("🎯 Целевое сканирование", self.targeted_scan, 3, 1),
            ("📈 Анализ трафика", self.traffic_analysis, 3, 2),
        ]

        for text, command, row, col in tools:
            btn = ttk.Button(tools_frame, text=text, command=command)
            btn.grid(row=row, column=col, sticky=tk.NSEW, padx=5, pady=5, ipady=10)

    def create_bottom_panel(self, parent):
        """Нижняя панель статуса"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        # Статус бар
        self.status_var = tk.StringVar(value="Готов")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, ipady=5)

        # Информация о сканирования
        info_frame = ttk.Frame(status_frame)
        info_frame.pack(fill=tk.X)

        self.scan_info = ttk.Label(info_frame, text="")
        self.scan_info.pack(side=tk.LEFT)

        self.time_label = ttk.Label(info_frame, text="")
        self.time_label.pack(side=tk.RIGHT)

        # Обновление времени
        self.update_time()

    def setup_context_menu(self):
        """Контекстное меню для результатов"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Открыть в браузере",
                                      command=self.open_selected_in_browser)
        self.context_menu.add_command(label="Скопировать порт",
                                      command=self.copy_port)
        self.context_menu.add_command(label="Проверить службу",
                                      command=self.check_service)
        self.context_menu.add_command(label="Добавить в избранное",
                                      command=self.add_to_favorites)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Получить баннер",
                                      command=self.get_banner)
        self.context_menu.add_command(label="Сохранить результат",
                                      command=self.save_selected_result)

        # Привязка правой кнопки
        self.results_tree.bind("<Button-3>", self.show_context_menu)

    # ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

    def log(self, message, level='INFO'):
        """Логирование"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        # В GUI
        self.logs_text.insert(tk.END, log_entry)
        self.logs_text.see(tk.END)

        # В файл
        if self.var_save_logs.get():
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            except:
                pass

        # В очередь для обновления статуса
        if level in ['ERROR', 'WARNING']:
            self.queue.put(('status', message))

    def update_time(self):
        """Обновление времени"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)

    def get_network_interfaces(self):
        """Получение сетевых интерфейсов без netifaces"""
        interfaces = []

        try:
            # Для Windows
            if platform.system() == "Windows":
                result = subprocess.run(['ipconfig'], capture_output=True, text=True)
                lines = result.stdout.split('\n')

                current_iface = None
                for line in lines:
                    if line.strip().endswith(':'):
                        current_iface = line.strip()[:-1]
                    elif 'IPv4 Address' in line or 'IPv4-адрес' in line:
                        if current_iface:
                            # Извлекаем IP адрес
                            parts = line.split(':')
                            if len(parts) > 1:
                                ip = parts[1].strip()
                                if ip != '':
                                    interfaces.append((current_iface, ip))
            else:
                # Для Linux/Mac
                result = subprocess.run(['ifconfig'], capture_output=True, text=True, shell=True)
                lines = result.stdout.split('\n')

                current_iface = None
                for line in lines:
                    if not line.startswith(' '):
                        # Название интерфейса
                        if ':' in line:
                            current_iface = line.split(':')[0]
                    elif 'inet ' in line and current_iface:
                        # Извлекаем IP
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            ip = parts[1]
                            interfaces.append((current_iface, ip))
        except:
            pass

        return interfaces

    def update_network_info(self):
        """Обновление информации о сети"""
        try:
            info = "=== СЕТЕВАЯ ИНФОРМАЦИЯ ===\n\n"

            # Хостнейм
            hostname = socket.gethostname()
            info += f"Имя компьютера: {hostname}\n"

            # IP адреса
            info += "\nIP адреса:\n"
            interfaces = self.get_network_interfaces()

            for iface_name, ip in interfaces:
                if not ip.startswith('127.'):
                    info += f"  {iface_name}: {ip}\n"

            # Шлюз по умолчанию (для Windows)
            if platform.system() == "Windows":
                info += "\nШлюз по умолчанию:\n"
                try:
                    result = subprocess.run(['ipconfig'], capture_output=True, text=True)
                    lines = result.stdout.split('\n')

                    for i, line in enumerate(lines):
                        if 'Default Gateway' in line or 'Основной шлюз' in line:
                            if i + 1 < len(lines):
                                gateway_line = lines[i + 1]
                                if ':' in gateway_line:
                                    gateway = gateway_line.split(':')[1].strip()
                                    if gateway:
                                        info += f"  {gateway}\n"
                except:
                    pass

            # DNS серверы
            info += "\nDNS серверы:\n"
            try:
                if platform.system() == "Windows":
                    result = subprocess.run(['ipconfig', '/all'],
                                            capture_output=True, text=True)
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'DNS Servers' in line or 'DNS-серверы' in line:
                            info += f"  {line.strip()}\n"
                else:
                    # Для Linux
                    result = subprocess.run(['cat', '/etc/resolv.conf'],
                                            capture_output=True, text=True)
                    for line in result.stdout.split('\n'):
                        if line.startswith('nameserver'):
                            dns = line.split()[1]
                            info += f"  {dns}\n"
            except:
                pass

            # Внешний IP
            info += "\nВнешний IP:\n"
            try:
                response = requests.get('https://api.ipify.org?format=json', timeout=5)
                if response.status_code == 200:
                    external_ip = response.json()['ip']
                    info += f"  {external_ip}\n"
            except:
                info += "  Не удалось определить\n"

            self.network_info.delete(1.0, tk.END)
            self.network_info.insert(1.0, info)

        except Exception as e:
            self.log(f"Ошибка получения сетевой информации: {e}", 'ERROR')

    def start_scan(self):
        """Начать сканирование"""
        if self.scanning:
            return

        try:
            host = self.host_var.get().strip()
            if not host:
                messagebox.showwarning("Внимание", "Введите хост для сканирования")
                return

            start_port = int(self.port_start.get())
            end_port = int(self.port_end.get())

            if start_port > end_port:
                messagebox.showwarning("Внимание", "Начальный порт должен быть меньше конечного")
                return

            # Очистка предыдущих результатов
            self.results_tree.delete(*self.results_tree.get_children())

            # Установка флагов
            self.scanning = True
            self.current_scan = {
                'host': host,
                'start_port': start_port,
                'end_port': end_port,
                'start_time': datetime.now(),
                'open_ports': [],
                'total_ports': end_port - start_port + 1
            }

            # Обновление GUI
            self.progress.start()
            self.status_var.set(f"Сканирование {host}...")

            # Запуск в отдельном потоке
            self.scan_thread = threading.Thread(target=self.scan_worker, daemon=True)
            self.scan_thread.start()

            self.log(f"Начато сканирование {host}:{start_port}-{end_port}", 'INFO')

        except Exception as e:
            self.log(f"Ошибка запуска сканирования: {e}", 'ERROR')
            messagebox.showerror("Ошибка", str(e))

    def scan_worker(self):
        """Рабочая функция сканирования"""
        try:
            host = self.current_scan['host']
            start_port = self.current_scan['start_port']
            end_port = self.current_scan['end_port']
            timeout = self.timeout_var.get()
            max_threads = self.threads_var.get()

            ports_to_scan = range(start_port, end_port + 1)
            open_ports = []

            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                # Создаем футуры для всех портов
                future_to_port = {
                    executor.submit(self.check_single_port, host, port, timeout): port
                    for port in ports_to_scan
                }

                completed = 0
                for future in as_completed(future_to_port):
                    if not self.scanning:
                        break

                    port = future_to_port[future]
                    try:
                        result = future.result(timeout=timeout + 1)
                        if result['open']:
                            open_ports.append(port)
                            self.queue.put(('result', result))
                    except Exception as e:
                        self.queue.put(('error', f"Порт {port}: {e}"))

                    completed += 1
                    progress = (completed / self.current_scan['total_ports']) * 100
                    self.queue.put(('progress', progress))

            # Завершение сканирования
            self.current_scan['end_time'] = datetime.now()
            self.current_scan['open_ports'] = open_ports

            duration = (self.current_scan['end_time'] -
                        self.current_scan['start_time']).total_seconds()

            self.queue.put(('scan_complete', {
                'host': host,
                'open_count': len(open_ports),
                'duration': duration,
                'method': self.scan_method.get()
            }))

            # Сохранение в историю
            self.save_to_history()

        except Exception as e:
            self.queue.put(('error', f"Ошибка сканирования: {e}"))
        finally:
            self.queue.put(('stop_scan', None))

    def check_single_port(self, host, port, timeout):
        """Проверка одного порта"""
        result = {
            'port': port,
            'open': False,
            'service': 'Неизвестно',
            'banner': '',
            'response': ''
        }

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            if sock.connect_ex((host, port)) == 0:
                result['open'] = True

                # Попытка получить сервис
                try:
                    result['service'] = socket.getservbyport(port)
                except:
                    pass

                # Попытка получить баннер
                try:
                    sock.send(b'HEAD / HTTP/1.0\r\n\r\n')
                    banner = sock.recv(1024).decode('utf-8', errors='ignore')
                    if banner:
                        result['banner'] = banner[:100]  # Ограничиваем длину

                        # Определяем тип сервиса по ответу
                        if 'HTTP' in banner.upper():
                            result['service'] = 'HTTP'
                        elif 'SMTP' in banner.upper():
                            result['service'] = 'SMTP'
                        elif 'FTP' in banner.upper():
                            result['service'] = 'FTP'
                        elif 'SSH' in banner.upper():
                            result['service'] = 'SSH'
                except:
                    pass

                sock.close()

                # Для HTTP портов пробуем получить больше информации
                if port in [80, 443, 8080, 8443]:
                    try:
                        protocol = 'https' if port in [443, 8443] else 'http'
                        response = requests.get(f'{protocol}://{host}:{port}',
                                                timeout=2, verify=False)
                        result['response'] = f"Status: {response.status_code}"
                    except:
                        pass

            return result

        except Exception as e:
            result['error'] = str(e)
            return result

    def pause_scan(self):
        """Пауза сканирования"""
        if self.scanning:
            self.scanning = False
            self.status_var.set("Сканирование приостановлено")
            self.progress.stop()
            self.log("Сканирование приостановлено", 'INFO')

    def stop_scan(self):
        """Остановка сканирования"""
        self.scanning = False
        self.status_var.set("Сканирование остановлено")
        self.progress.stop()
        self.log("Сканирование остановлено", 'INFO')

    def check_queue(self):
        """Проверка очереди событий"""
        try:
            while True:
                msg_type, data = self.queue.get_nowait()

                if msg_type == 'result':
                    self.add_result_to_tree(data)

                elif msg_type == 'progress':
                    # Можно добавить progress bar
                    pass

                elif msg_type == 'status':
                    self.status_var.set(data)

                elif msg_type == 'error':
                    self.log(data, 'ERROR')

                elif msg_type == 'scan_complete':
                    self.handle_scan_complete(data)

                elif msg_type == 'stop_scan':
                    self.scanning = False
                    self.progress.stop()
                    self.status_var.set("Готов")

        except Empty:
            pass

        self.root.after(100, self.check_queue)

    def add_result_to_tree(self, result):
        """Добавление результата в дерево"""
        if not result['open'] and not self.var_show_closed.get():
            return

        tags = ()
        if result['open']:
            tags = ('open',)
            if self.var_auto_open.get() and result['port'] in [80, 443, 8080]:
                self.open_in_browser(f"http://{self.current_scan['host']}:{result['port']}")

        self.results_tree.insert('', 'end', values=(
            result['port'],
            '✅ Открыт' if result['open'] else '❌ Закрыт',
            result['service'],
            result['banner'][:50] if result['banner'] else '',
            result['response']
        ), tags=tags)

    def handle_scan_complete(self, data):
        """Обработка завершения сканирования"""
        self.log(f"Сканирование завершено. Открыто портов: {data['open_count']}. "
                 f"Время: {data['duration']:.2f} сек", 'INFO')

        self.status_var.set(f"Готов. Найдено {data['open_count']} открытых портов")

        # Обновление статистики
        stats_text = f"Отсканировано: {self.current_scan['total_ports']} портов | "
        stats_text += f"Открыто: {data['open_count']} | "
        stats_text += f"Время: {data['duration']:.2f} сек"
        self.stats_label.config(text=stats_text)

        # Показать уведомление
        if data['open_count'] > 0:
            messagebox.showinfo("Сканирование завершено",
                                f"Найдено {data['open_count']} открытых портов")

    # ==================== ИНСТРУМЕНТЫ ====================

    def get_local_ip_range(self):
        """Получение локального IP диапазона"""
        try:
            # Получаем IP адрес локального хоста
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Подключаемся к публичному DNS серверу
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            finally:
                s.close()

            # Определяем подсеть по умолчанию (обычно /24)
            ip_parts = local_ip.split('.')
            if len(ip_parts) == 4:
                return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
        except:
            pass

        return "192.168.1.0/24"  # Значение по умолчанию

    def scan_local_network(self):
        """Сканирование локальной сети"""
        try:
            network_str = self.get_local_ip_range()
            self.log(f"Сканирование сети: {network_str}", 'INFO')

            network = ipaddress.ip_network(network_str, strict=False)

            # Сканируем первые 20 адресов
            hosts = list(network.hosts())[:20]

            for host in hosts:
                threading.Thread(
                    target=self.ping_host,
                    args=(str(host),),
                    daemon=True
                ).start()

        except Exception as e:
            self.log(f"Ошибка сканирования сети: {e}", 'ERROR')

    def ping_host(self, ip):
        """Пинг хоста"""
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            result = subprocess.run(['ping', param, '1', '-w', '1000', ip],
                                    capture_output=True, text=True)

            if "TTL" in result.stdout or "ttl" in result.stdout.lower():
                self.queue.put(('status', f"Найден хост: {ip}"))

                # Проверяем порт 80
                sock = socket.socket()
                sock.settimeout(1)
                if sock.connect_ex((ip, 80)) == 0:
                    self.queue.put(('status', f"  → Веб-сервер на {ip}:80"))
                sock.close()
        except:
            pass

    def open_port_tool(self):
        """Инструмент открытия порта"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Открытие порта")
        dialog.geometry("400x300")

        ttk.Label(dialog, text="Номер порта:").pack(pady=10)
        port_entry = ttk.Entry(dialog)
        port_entry.pack(pady=5)

        ttk.Label(dialog, text="Протокол:").pack(pady=10)
        protocol_var = tk.StringVar(value="TCP")
        ttk.Combobox(dialog, textvariable=protocol_var,
                     values=["TCP", "UDP"], state='readonly').pack(pady=5)

        ttk.Label(dialog, text="Направление:").pack(pady=10)
        direction_var = tk.StringVar(value="Входящий")
        ttk.Combobox(dialog, textvariable=direction_var,
                     values=["Входящий", "Исходящий", "Оба"],
                     state='readonly').pack(pady=5)

        def open_port():
            try:
                port = int(port_entry.get())
                protocol = protocol_var.get()
                direction = direction_var.get()

                if platform.system() == "Windows":
                    if direction in ["Входящий", "Оба"]:
                        cmd = ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                               f'name=OpenPort{port}In',
                               'dir=in',
                               'action=allow',
                               f'protocol={protocol}',
                               f'localport={port}']
                        subprocess.run(cmd, capture_output=True)

                    if direction in ["Исходящий", "Оба"]:
                        cmd = ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                               f'name=OpenPort{port}Out',
                               'dir=out',
                               'action=allow',
                               f'protocol={protocol}',
                               f'localport={port}']
                        subprocess.run(cmd, capture_output=True)

                    messagebox.showinfo("Успех", f"Порт {port} открыт")
                    self.log(f"Открыт порт {port}/{protocol} ({direction})", 'INFO')

                else:
                    messagebox.showinfo("Информация",
                                        "На Linux/Mac используйте iptables/ufw")

            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
                self.log(f"Ошибка открытия порта: {e}", 'ERROR')

        ttk.Button(dialog, text="Открыть порт", command=open_port).pack(pady=20)

    def open_in_browser(self, url_template):
        """Открытие URL в браузере"""
        try:
            host = self.host_var.get().strip()
            url = url_template.format(host=host)

            # Проверяем доступность
            try:
                response = requests.head(url, timeout=2, verify=False)
                if response.status_code < 400:
                    webbrowser.open(url)
                    self.log(f"Открыт {url}", 'INFO')
                else:
                    self.log(f"Сервер недоступен: {url}", 'WARNING')
            except:
                # Все равно пробуем открыть
                webbrowser.open(url)
                self.log(f"Попытка открыть {url}", 'INFO')

        except Exception as e:
            self.log(f"Ошибка открытия браузера: {e}", 'ERROR')

    def open_selected_in_browser(self):
        """Открыть выбранный порт в браузере"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            port = item['values'][0]
            host = self.host_var.get().strip()

            protocol = 'https' if port in [443, 8443] else 'http'
            url = f"{protocol}://{host}:{port}"

            webbrowser.open(url)
            self.log(f"Открыт {url}", 'INFO')

    def browser_go(self):
        """Перейти по URL в мини-браузере"""
        if HAS_TKINTERWEB:
            url = self.browser_url.get().strip()
            if url:
                try:
                    self.html_frame.load_url(url)
                    self.log(f"Загружено: {url}", 'INFO')
                except Exception as e:
                    self.log(f"Ошибка загрузки: {e}", 'ERROR')

    def browser_back(self):
        """Назад в браузере"""
        if HAS_TKINTERWEB:
            try:
                self.html_frame.back()
            except:
                pass

    def browser_forward(self):
        """Вперед в браузере"""
        if HAS_TKINTERWEB:
            try:
                self.html_frame.forward()
            except:
                pass

    def browser_refresh(self):
        """Обновить страницу в браузере"""
        if HAS_TKINTERWEB:
            try:
                self.html_frame.reload()
            except:
                pass

    # ==================== ИСТОРИЯ И СОХРАНЕНИЕ ====================

    def save_to_history(self):
        """Сохранение в историю"""
        try:
            scan_record = {
                'id': str(time.time()),
                'date': datetime.now().isoformat(),
                'host': self.current_scan['host'],
                'start_port': self.current_scan['start_port'],
                'end_port': self.current_scan['end_port'],
                'open_ports': self.current_scan['open_ports'],
                'duration': (self.current_scan['end_time'] -
                             self.current_scan['start_time']).total_seconds(),
                'method': self.scan_method.get(),
                'total_ports': self.current_scan['total_ports']
            }

            self.scan_history.append(scan_record)

            # Сохраняем в файл
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.scan_history, f, ensure_ascii=False, indent=2)

            # Обновляем GUI
            self.update_history_gui()

        except Exception as e:
            self.log(f"Ошибка сохранения истории: {e}", 'ERROR')

    def load_history(self):
        """Загрузка истории из файла"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return []

    def update_history_gui(self):
        """Обновление истории в GUI"""
        # Очищаем текущее
        self.history_tree.delete(*self.history_tree.get_children())

        # Добавляем записи (последние 50)
        for record in self.scan_history[-50:]:
            date = datetime.fromisoformat(record['date']).strftime("%Y-%m-%d %H:%M")
            ports = f"{record['start_port']}-{record['end_port']}"

            self.history_tree.insert('', 'end', values=(
                date,
                record['host'],
                ports,
                len(record['open_ports']),
                f"{record['duration']:.1f}с",
                record.get('method', 'N/A')
            ))

    def clear_history(self):
        """Очистка истории"""
        if messagebox.askyesno("Подтверждение", "Очистить всю историю?"):
            self.scan_history = []
            self.history_tree.delete(*self.history_tree.get_children())
            try:
                os.remove(self.history_file)
            except:
                pass
            self.log("История очищена", 'INFO')

    def repeat_scan(self):
        """Повторить выбранное сканирование"""
        selection = self.history_tree.selection()
        if selection:
            item = self.history_tree.item(selection[0])
            host = item['values'][1]

            self.host_var.set(host)
            self.start_scan()

    # ==================== СОХРАНЕНИЕ И ЭКСПОРТ ====================

    def save_results(self):
        """Сохранение результатов"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[
                    ("JSON files", "*.json"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                results = []
                for item in self.results_tree.get_children():
                    values = self.results_tree.item(item)['values']
                    results.append({
                        'port': values[0],
                        'status': values[1],
                        'service': values[2],
                        'banner': values[3],
                        'response': values[4]
                    })

                data = {
                    'scan_info': self.current_scan,
                    'results': results,
                    'export_date': datetime.now().isoformat()
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                self.log(f"Результаты сохранены в {filename}", 'INFO')
                messagebox.showinfo("Успех", "Результаты сохранены")

        except Exception as e:
            self.log(f"Ошибка сохранения: {e}", 'ERROR')
            messagebox.showerror("Ошибка", str(e))

    def generate_report(self):
        """Генерация отчета"""
        try:
            report = "=== ОТЧЕТ СКАНИРОВАНИЯ ПОРТОВ ===\n\n"

            if self.current_scan:
                report += f"Цель: {self.current_scan['host']}\n"
                report += f"Диапазон портов: {self.current_scan['start_port']}-{self.current_scan['end_port']}\n"
                report += f"Время начала: {self.current_scan['start_time']}\n"

                if 'end_time' in self.current_scan:
                    duration = self.current_scan['end_time'] - self.current_scan['start_time']
                    report += f"Длительность: {duration.total_seconds():.2f} сек\n"
                    report += f"Найдено открытых портов: {len(self.current_scan['open_ports'])}\n\n"

            report += "ОТКРЫТЫЕ ПОРТЫ:\n"
            report += "-" * 80 + "\n"

            open_ports = []
            for item in self.results_tree.get_children():
                values = self.results_tree.item(item)['values']
                if '✅' in values[1]:  # Открытый порт
                    open_ports.append(values)

            if open_ports:
                for port, status, service, banner, response in open_ports:
                    report += f"Порт {port}: {service}\n"
                    if banner:
                        report += f"  Баннер: {banner[:100]}...\n"
                    if response:
                        report += f"  Ответ: {response}\n"
                    report += "\n"
            else:
                report += "Нет открытых портов\n"

            # Показываем отчет
            dialog = tk.Toplevel(self.root)
            dialog.title("Отчет сканирования")
            dialog.geometry("800x600")

            text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(1.0, report)

            ttk.Button(dialog, text="Сохранить",
                       command=lambda: self.save_text_to_file(report)).pack(pady=10)

        except Exception as e:
            self.log(f"Ошибка генерации отчета: {e}", 'ERROR')

    def save_text_to_file(self, text):
        """Сохранение текста в файл"""
        try:
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

                self.log(f"Отчет сохранен в {filename}", 'INFO')
                messagebox.showinfo("Успех", "Отчет сохранен")

        except Exception as e:
            self.log(f"Ошибка сохранения отчета: {e}", 'ERROR')

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def set_port_range(self, ports):
        """Установка диапазона портов"""
        if len(ports) == 2:
            self.port_start.delete(0, tk.END)
            self.port_start.insert(0, str(ports[0]))
            self.port_end.delete(0, tk.END)
            self.port_end.insert(0, str(ports[1]))
        else:
            # Для списка портов
            self.port_start.delete(0, tk.END)
            self.port_start.insert(0, str(min(ports)))
            self.port_end.delete(0, tk.END)
            self.port_end.insert(0, str(max(ports)))

    def show_context_menu(self, event):
        """Показать контекстное меню"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_port(self):
        """Копировать номер порта"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            port = item['values'][0]
            self.root.clipboard_clear()
            self.root.clipboard_append(str(port))
            self.log(f"Скопирован порт: {port}", 'INFO')

    def clear_results(self):
        """Очистка результатов"""
        self.results_tree.delete(*self.results_tree.get_children())
        self.stats_label.config(text="")
        self.log("Результаты очищены", 'INFO')

    def clear_logs(self):
        """Очистка логов"""
        self.logs_text.delete(1.0, tk.END)
        self.log("Логи очищены", 'INFO')

    def save_logs(self):
        """Сохранение логов"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[
                    ("Log files", "*.log"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                logs = self.logs_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(logs)

                self.log(f"Логи сохранены в {filename}", 'INFO')
                messagebox.showinfo("Успех", "Логи сохранены")

        except Exception as e:
            self.log(f"Ошибка сохранения логов: {e}", 'ERROR')

    def export_logs(self):
        """Экспорт логов"""
        self.save_logs()

    def load_history_gui(self):
        """Загрузка истории в GUI"""
        self.update_history_gui()
        self.log("История загружена", 'INFO')

    def export_history_csv(self):
        """Экспорт истории в CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Дата', 'Цель', 'Порты', 'Открыто', 'Время', 'Метод'])

                    for record in self.scan_history[-100:]:  # Последние 100 записей
                        date = datetime.fromisoformat(record['date']).strftime("%Y-%m-%d %H:%M")
                        ports = f"{record['start_port']}-{record['end_port']}"

                        writer.writerow([
                            date,
                            record['host'],
                            ports,
                            len(record['open_ports']),
                            f"{record['duration']:.1f}",
                            record.get('method', 'N/A')
                        ])

                self.log(f"История экспортирована в {filename}", 'INFO')
                messagebox.showinfo("Успех", "История экспортирована")

        except Exception as e:
            self.log(f"Ошибка экспорта истории: {e}", 'ERROR')

    def open_settings(self):
        """Открыть настройки"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки")
        dialog.geometry("500x400")

        # Закладки в настройках
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка общих настроек
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="Общие")

        ttk.Label(general_frame, text="Максимальное количество потоков:").pack(pady=5)
        max_threads = ttk.Spinbox(general_frame, from_=1, to=1000, width=10)
        max_threads.pack(pady=5)
        max_threads.set(self.threads_var.get())

        ttk.Label(general_frame, text="Таймаут по умолчанию (сек):").pack(pady=5)
        default_timeout = ttk.Entry(general_frame, width=10)
        default_timeout.pack(pady=5)
        default_timeout.insert(0, str(self.timeout_var.get()))

        # Вкладка сохранения
        save_frame = ttk.Frame(notebook)
        notebook.add(save_frame, text="Сохранение")

        self.var_auto_save = tk.BooleanVar(value=True)
        ttk.Checkbutton(save_frame, text="Автосохранение результатов",
                        variable=self.var_auto_save).pack(pady=5)

        ttk.Checkbutton(save_frame, text="Сохранять логи в файл",
                        variable=self.var_save_logs).pack(pady=5)

        # Вкладка интерфейса
        ui_frame = ttk.Frame(notebook)
        notebook.add(ui_frame, text="Интерфейс")

        self.var_dark_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(ui_frame, text="Темная тема",
                        variable=self.var_dark_mode).pack(pady=5)

        ttk.Checkbutton(ui_frame, text="Показывать закрытые порты",
                        variable=self.var_show_closed).pack(pady=5)

        def save_settings():
            try:
                self.threads_var.set(int(max_threads.get()))
                self.timeout_var.set(float(default_timeout.get()))

                # Сохранение в конфиг
                config = {
                    'threads': self.threads_var.get(),
                    'timeout': self.timeout_var.get(),
                    'auto_save': self.var_auto_save.get(),
                    'save_logs': self.var_save_logs.get(),
                    'dark_mode': self.var_dark_mode.get(),
                    'show_closed': self.var_show_closed.get()
                }

                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                self.log("Настройки сохранены", 'INFO')
                dialog.destroy()

            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        ttk.Button(dialog, text="Сохранить", command=save_settings).pack(pady=20)

    def load_config(self):
        """Загрузка конфигурации"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.threads_var.set(config.get('threads', 100))
                self.timeout_var.set(config.get('timeout', 1.0))
                self.var_auto_save.set(config.get('auto_save', True))
                self.var_save_logs.set(config.get('save_logs', True))
                self.var_show_closed.set(config.get('show_closed', False))

                if config.get('dark_mode', False):
                    self.apply_dark_theme()

        except Exception as e:
            self.log(f"Ошибка загрузки конфигурации: {e}", 'ERROR')

    def apply_dark_theme(self):
        """Применение темной темы"""
        try:
            self.root.configure(bg='#2b2b2b')
            self.style.theme_use('alt')
        except:
            pass

    def auto_save(self):
        """Автосохранение"""
        if self.var_auto_save.get() and self.current_scan:
            try:
                temp_file = f"autosave_{int(time.time())}.json"
                data = {
                    'current_scan': self.current_scan,
                    'timestamp': datetime.now().isoformat()
                }

                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # Удаляем старые автосейвы (оставляем последние 5)
                import glob
                autosaves = glob.glob("autosave_*.json")
                autosaves.sort(key=os.path.getmtime, reverse=True)

                for old_file in autosaves[5:]:
                    try:
                        os.remove(old_file)
                    except:
                        pass

            except:
                pass

        # Планируем следующее автосохранение
        self.root.after(30000, self.auto_save)

    # ==================== ДОПОЛНИТЕЛЬНЫЕ ИНСТРУМЕНТЫ ====================

    def close_port_tool(self):
        """Закрытие порта"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Закрытие порта")
        dialog.geometry("400x200")

        ttk.Label(dialog, text="Номер порта:").pack(pady=10)
        port_entry = ttk.Entry(dialog)
        port_entry.pack(pady=5)

        def close_port():
            try:
                port = int(port_entry.get())

                if platform.system() == "Windows":
                    # Удаляем правила брандмауэра
                    cmds = [
                        ['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                         f'name=OpenPort{port}In'],
                        ['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                         f'name=OpenPort{port}Out']
                    ]

                    for cmd in cmds:
                        try:
                            subprocess.run(cmd, capture_output=True)
                        except:
                            pass

                    messagebox.showinfo("Успех", f"Порт {port} закрыт")
                    self.log(f"Закрыт порт {port}", 'INFO')

                else:
                    messagebox.showinfo("Информация",
                                        "На Linux/Mac используйте iptables/ufw")

            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
                self.log(f"Ошибка закрытия порта: {e}", 'ERROR')

        ttk.Button(dialog, text="Закрыть порт", command=close_port).pack(pady=20)
    '''
    def ping_tool(self):
        """Инструмент ping"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Ping инструмент")
        dialog.geometry("500x400")

        ttk.Label(dialog, text="Хост/IP:").pack(pady=10)
        host_entry = ttk.Entry(dialog, width=30)
        host_entry.pack(pady=5)
        host_entry.insert(0, self.host_var.get())

        ttk.Label(dialog, text="Количество пакетов:").pack(pady=10)
        count_entry = ttk.Spinbox(dialog, from_=1, to=100, width=10)
        count_entry.pack(pady=5)
        count_entry.set(4)

        output_text = scrolledtext.ScrolledText(dialog, height=15)
        output_text.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        def do_ping():
            host = host_entry.get().strip()
            count = count_entry.get()

            if not host:
                messagebox.showwarning("Внимание", "Введите хост")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Pinging {host}...\n\n")

            try:
                param = '-n' if platform.system().lower() == 'windows' else '-c'
                result = subprocess.run(['ping', param, count, host],
                                        capture_output=True, text=True, timeout=10)

                output_text.insert(tk.END, result.stdout)
                output_text.insert(tk.END, "\n" + result.stderr)

                self.log(f"Выполнен ping {host}", 'INFO')

            except Exception as e:
                output_text.insert(tk.END, f"Ошибка: {e}")
                self.log(f"Ошибка ping: {e}", 'ERROR')

        ttk.Button(dialog, text="Выполнить ping", command=do_ping).pack(pady=10)
    '''
    def export_network_info(self):
        """Экспорт сетевой информации"""
        try:
            info = self.network_info.get(1.0, tk.END)
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(info)

                self.log(f"Сетевая информация экспортирована", 'INFO')
                messagebox.showinfo("Успех", "Информация экспортирована")

        except Exception as e:
            self.log(f"Ошибка экспорта: {e}", 'ERROR')

    # ==================== МЕТОДЫ-ЗАГЛУШКИ ДЛЯ ИНСТРУМЕНТОВ ====================

    def traceroute_tool(self):
        self.log("Traceroute инструмент (в разработке)", 'INFO')
        messagebox.showinfo("Информация", "Функция в разработке")

    def dns_lookup_tool(self):
        self.log("DNS Lookup инструмент (в разработке)", 'INFO')
        messagebox.showinfo("Информация", "Функция в разработке")

    def bandwidth_test(self):
        self.log("Тест пропускной способности (в разработке)", 'INFO')
        messagebox.showinfo("Информация", "Функция в разработке")

    def firewall_check(self):
        self.log("Проверка брандмауэра (в разработке)", 'INFO')
        messagebox.showinfo("Информация", "Функция в разработке")

    def start_server_tool(self):
        self.log("Запуск сервера (в разработке)", 'INFO')
        messagebox.showinfo("Информация", "Функция в разработке")

    def network_monitor(self):
        self.log("Монитор сети (в разработке)", 'INFO')
        messagebox.showinfo("Информация", "Функция в разработке")

    def quick_scan(self):
        self.log("Быстрое сканирование", 'INFO')
        self.set_port_range((1, 1000))
        self.start_scan()

    def targeted_scan(self):
        dialog = tk.Toplevel(self.root)
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
        self.set_port_range((min(ports), max(ports)))
        self.start_scan()

    def traffic_analysis(self):
        self.log("Анализ трафика (в разработке)", 'INFO')
        messagebox.showinfo("Информация", "Функция в разработке")

    def check_service(self):
        """Проверка службы на выбранном порту"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            port = item['values'][0]
            service = item['values'][2]

            messagebox.showinfo("Информация о службе",
                                f"Порт: {port}\nСлужба: {service}\n\n"
                                f"Распространенные службы на этом порту:\n"
                                f"{self.get_service_info(port)}")

    def get_service_info(self, port):
        """Получить информацию о службе по порту"""
        common_services = {
            21: "FTP - File Transfer Protocol",
            22: "SSH - Secure Shell",
            23: "Telnet",
            25: "SMTP - Simple Mail Transfer Protocol",
            53: "DNS - Domain Name System",
            80: "HTTP - HyperText Transfer Protocol",
            110: "POP3 - Post Office Protocol v3",
            143: "IMAP - Internet Message Access Protocol",
            443: "HTTPS - HTTP Secure",
            465: "SMTPS - SMTP Secure",
            993: "IMAPS - IMAP Secure",
            995: "POP3S - POP3 Secure",
            3306: "MySQL Database",
            3389: "RDP - Remote Desktop Protocol",
            5432: "PostgreSQL Database",
            5900: "VNC - Virtual Network Computing",
            8080: "HTTP Proxy / Alternative HTTP",
            8443: "HTTPS Alternative",
            27017: "MongoDB Database",
        }

        return common_services.get(port, "Неизвестная служба")

    def add_to_favorites(self):
        """Добавить в избранное"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            port = item['values'][0]
            host = self.host_var.get()

            try:
                with open('favorites.json', 'r', encoding='utf-8') as f:
                    favorites = json.load(f)
            except:
                favorites = []

            favorite = {
                'host': host,
                'port': port,
                'service': item['values'][2],
                'added': datetime.now().isoformat()
            }

            favorites.append(favorite)

            with open('favorites.json', 'w', encoding='utf-8') as f:
                json.dump(favorites, f, ensure_ascii=False, indent=2)

            self.log(f"Добавлено в избранное: {host}:{port}", 'INFO')
            messagebox.showinfo("Успех", "Добавлено в избранное")

    def get_banner(self):
        """Получить баннер службы"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            port = item['values'][0]
            host = self.host_var.get()

            self.log(f"Получение баннера для {host}:{port}", 'INFO')

            # В отдельном потоке
            threading.Thread(target=self.fetch_banner,
                             args=(host, port),
                             daemon=True).start()

    def fetch_banner(self, host, port):
        """Получить баннер службы"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)

            if sock.connect_ex((host, port)) == 0:
                # Пробуем разные команды для разных протоколов
                if port in [21, 2121]:  # FTP
                    sock.send(b'\r\n')
                elif port in [22]:  # SSH
                    sock.send(b'SSH-2.0-Client\r\n')
                elif port in [25, 587]:  # SMTP
                    sock.send(b'EHLO example.com\r\n')
                elif port in [80, 443, 8080, 8443]:  # HTTP/S
                    sock.send(b'HEAD / HTTP/1.0\r\n\r\n')
                else:
                    sock.send(b'\r\n')

                banner = sock.recv(1024).decode('utf-8', errors='ignore')
                sock.close()

                if banner:
                    self.queue.put(('banner', f"Баннер {host}:{port}:\n{banner}"))
                else:
                    self.queue.put(('banner', f"Нет баннера на {host}:{port}"))
            else:
                self.queue.put(('banner', f"Порт {port} закрыт"))

        except Exception as e:
            self.queue.put(('banner', f"Ошибка: {e}"))

    def save_selected_result(self):
        """Сохранить выбранный результат"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])

            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Результат сканирования:\n")
                    f.write(f"Хост: {self.host_var.get()}\n")
                    f.write(f"Порт: {item['values'][0]}\n")
                    f.write(f"Статус: {item['values'][1]}\n")
                    f.write(f"Служба: {item['values'][2]}\n")
                    f.write(f"Баннер: {item['values'][3]}\n")
                    f.write(f"Ответ: {item['values'][4]}\n")

                self.log(f"Результат сохранен в {filename}", 'INFO')
                messagebox.showinfo("Успех", "Результат сохранен")

    def scan_network(self):
        """Сканирование сети (альтернативная реализация)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Сканирование сети")
        dialog.geometry("400x200")

        ttk.Label(dialog, text="Диапазон IP (например: 192.168.1.0/24):").pack(pady=10)

        ip_var = tk.StringVar(value=self.get_local_ip_range())
        ip_entry = ttk.Entry(dialog, textvariable=ip_var, width=30)
        ip_entry.pack(pady=5)

        ttk.Label(dialog, text="Количество хостов (макс 50):").pack(pady=10)
        count_var = tk.IntVar(value=20)
        count_spin = ttk.Spinbox(dialog, from_=1, to=50, textvariable=count_var, width=10)
        count_spin.pack(pady=5)

        def start_network_scan():
            try:
                network_str = ip_var.get()
                count = count_var.get()

                network = ipaddress.ip_network(network_str, strict=False)
                hosts = list(network.hosts())[:count]

                self.log(f"Начато сканирование сети {network_str}", 'INFO')
                dialog.destroy()

                for host in hosts:
                    threading.Thread(
                        target=self.ping_host,
                        args=(str(host),),
                        daemon=True
                    ).start()

            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        ttk.Button(dialog, text="Начать сканирование", command=start_network_scan).pack(pady=20)


def main():
    """Запуск приложения"""
    root = tk.Tk()

    # Улучшаем DPI для Windows
    if platform.system() == "Windows":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

    app = MegaPortScanner(root)

    # Центрируем окно
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'1400x800+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    # Проверка зависимостей
    dependencies = ['requests']
    missing = []

    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    if missing:
        print("⚠️ Установите недостающие зависимости:")
        print(f"   pip install {' '.join(missing)}")
        print("\nДля мини-браузера также установите:")
        print("   pip install tkinterweb")
        input("\nНажмите Enter для выхода...")
    else:
        main()