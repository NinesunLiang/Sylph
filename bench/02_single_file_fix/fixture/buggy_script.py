#!/usr/bin/env python3
"""buggy_script.py — 包含一个 off-by-one 错误的列表处理函数"""

def get_item(items, index):
    """返回列表中指定索引的元素。索引从 1 开始计数。"""
    return items[index - 1]


def main():
    data = [10, 20, 30, 40, 50]
    idx = int(input("Enter index (1-5): "))
    result = get_item(data, idx)
    print(f"Item at position {idx}: {result}")


if __name__ == "__main__":
    main()
