# В методе setup_tools_tab() заменяем список инструментов:

def setup_tools_tab(self):
    """Вкладка инструментов"""
    tools_frame = ttk.Frame(self.tab_tools)
    tools_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Создаем Notebook для группировки инструментов
    tools_notebook = ttk.Notebook(tools_frame)
    tools_notebook.pack(fill=tk.BOTH, expand=True)

    # Вкладка 1: Основные инструменты
    basic_frame = ttk.Frame(tools_notebook)
    tools_notebook.add(basic_frame, text="Основные")

    # Вкладка 2: Сканирование сети
    scanning_frame = ttk.Frame(tools_notebook)
    tools_notebook.add(scanning_frame, text="Сканирование")

    # Вкладка 3: Безопасность
    security_frame = ttk.Frame(tools_notebook)
    tools_notebook.add(security_frame, text="Безопасность")

    # Вкладка 4: Анализ
    analysis_frame = ttk.Frame(tools_notebook)
    tools_notebook.add(analysis_frame, text="Анализ")

    # Вкладка 5: Дополнительно
    advanced_frame = ttk.Frame(tools_notebook)
    tools_notebook.add(advanced_frame, text="Дополнительно")

    if self.tools:
        # Основные инструменты
        basic_tools = [
            ("🔧 Открыть порт", self.tools.open_port_tool, 0, 0),
            ("🔒 Закрыть порт", self.tools.close_port_tool, 0, 1),
            ("📡 Ping хоста", self.tools.ping_tool, 1, 0),
            ("🌐 Traceroute", self.tools.traceroute_tool, 1, 1),
            ("🔍 DNS lookup", self.tools.dns_lookup_tool, 2, 0),
            ("📊 Пропускная способность", self.tools.bandwidth_test, 2, 1),
            ("🛡️ Проверка брандмауэра", self.tools.firewall_check, 3, 0),
            ("🚀 Запустить сервер", self.tools.start_server_tool, 3, 1),
        ]

        # Инструменты сканирования
        scanning_tools = [
            ("📶 Монитор сети", self.tools.network_monitor, 0, 0),
            ("⚡ Быстрый скан", self.tools.quick_scan, 0, 1),
            ("🎯 Целевое сканирование", self.tools.targeted_scan, 1, 0),
            ("📈 Анализ трафика", self.tools.traffic_analysis, 1, 1),
            ("🔧 Настройка сети", self.tools.network_setup, 2, 0),
            ("🔐 Проверка SSL", self.tools.ssl_check, 2, 1),
            ("📡 WHOIS запрос", self.tools.whois_lookup, 3, 0),
            ("🗺️ Карта сети", self.tools.network_mapper, 3, 1),
        ]

        # Инструменты безопасности
        security_tools = [
            ("⚠️ Сканер уязвимостей", self.tools.vulnerability_scanner, 0, 0),
            ("📡 Сниффер пакетов", self.tools.packet_sniffer, 0, 1),
            ("🌐 Сканер поддоменов", self.tools.subdomain_scanner, 1, 0),
            ("📶 Сканер Wi-Fi", self.tools.wifi_scanner, 1, 1),
            ("🔓 Тестер паролей", self.tools.password_cracker_tool, 2, 0),
        ]

        # Инструменты анализа
        analysis_tools = [
            ("📊 Проброс портов", self.tools.port_forwarding_tool, 0, 0),
            ("🔍 Анализ заголовков", self.analyze_headers_tool, 0, 1),
            ("📝 Генератор отчетов", self.report_generator, 1, 0),
            ("📊 Статистика сети", self.network_statistics, 1, 1),
        ]

        # Дополнительные инструменты
        advanced_tools = [
            ("⚙️ Настройки приложения", self.open_settings, 0, 0),
            ("💾 Резервное копирование", self.backup_config, 0, 1),
            ("🔄 Обновить базы", self.update_databases, 1, 0),
            ("📚 Справка", self.show_help, 1, 1),
        ]

        # Создаем сетки для каждой вкладки
        for frame, tools_list in [
            (basic_frame, basic_tools),
            (scanning_frame, scanning_tools),
            (security_frame, security_tools),
            (analysis_frame, analysis_tools),
            (advanced_frame, advanced_tools)
        ]:
            for i in range(4):
                frame.columnconfigure(i, weight=1)
            for i in range(8):
                frame.rowconfigure(i, weight=1)

            for text, command, row, col in tools_list:
                btn = ttk.Button(frame, text=text, command=command)
                btn.grid(row=row, column=col, sticky=tk.NSEW, padx=5, pady=5, ipady=10)

    else:
        error_label = ttk.Label(tools_frame,
                                text="⚠ Инструменты не загружены\nУбедитесь, что advanced_scanner_tools.py находится в той же папке",
                                justify=tk.CENTER)
        error_label.pack(expand=True)


# Добавляем новые методы в класс MegaPortScanner:



