# test.py
# 這是一個簡單的 Python 測試程式

def say_hello(name):
    return f"Hello, {name}! 👋"

def add_numbers(a, b):
    return a + b

if __name__ == "__main__":
    # 測試 say_hello()
    print(say_hello("VS Code"))

    # 測試 add_numbers()
    x, y = 5, 7
    print(f"{x} + {y} = {add_numbers(x, y)}")

    # 確認 Python 可以正常執行
    print("✅ Python 測試完成！")
