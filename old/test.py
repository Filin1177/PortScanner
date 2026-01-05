# Вставьте это в ваш код
PEPPER_HEX = "6d795f626573745f6d6163655f7076705f7065707065725f6c6f6f6b5f6f6e5f69745f6f5f6f5f67672e6d6163652e707670"

# Функция для получения перца (если нужна)
def get_pepper():
    return bytes.fromhex(PEPPER_HEX).decode()

# Или сразу как строку
PEPPER = bytes.fromhex(PEPPER_HEX).decode()
print(PEPPER)

