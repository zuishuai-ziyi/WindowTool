import hashlib
import os

# 文件路径
dll_path = 'UIAccess.dll'

# 检查文件是否存在
if not os.path.exists(dll_path):
    print(f"文件 {dll_path} 不存在")
    exit(1)

# 获取文件大小
file_size = os.path.getsize(dll_path)
print(f"文件大小: {file_size} 字节")

# 计算各种哈希值
hash_methods = {
    'md5': hashlib.md5,
    'sha1': hashlib.sha1,
    'sha224': hashlib.sha224,
    'sha256': hashlib.sha256,
    'sha384': hashlib.sha384,
    'sha512': hashlib.sha512,
    'blake2b': hashlib.blake2b,
    'blake2s': hashlib.blake2s,
    'sha3_224': hashlib.sha3_224,
    'sha3_256': hashlib.sha3_256,
}

# 读取文件内容
with open(dll_path, 'rb') as f:
    file_content = f.read()

# 计算并打印哈希值
print("\n哈希值:")
for name, method in hash_methods.items():
    hash_obj = method(file_content)
    print(f"{name}: {hash_obj.hexdigest()}")

print("\n请将以上值复制到 api.py 文件中的对应常量")