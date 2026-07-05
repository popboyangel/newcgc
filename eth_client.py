# -*- coding: utf-8 -*-
"""
eth_client.py
==============
轻量级 EVM JSON-RPC 客户端，不依赖 web3.py。

为什么不用 web3.py？
    web3.py 依赖 eth-abi / eth-hash / pycryptodome 等大量 C 扩展库，
    在 buildozer / python-for-android 上非常容易编译失败（这也是
    之前 APK 构建卡住的常见原因之一）。这里只用标准库 + requests，
    手动做 ABI 编码/解码，兼容性和构建成功率都高很多。
"""

import requests

# 常用函数的 4 字节选择器（keccak256(签名) 的前 4 字节），
# 这几个都是标准 ERC20 / UniswapV2 Pair 接口，选择器是固定值，不用现算。
SELECTOR_GET_RESERVES = "0x0902f1ac"  # getReserves()
SELECTOR_DECIMALS = "0x313ce567"      # decimals()
SELECTOR_SYMBOL = "0x95d89b41"        # symbol()


class RpcError(Exception):
    pass


def eth_call(rpc_url: str, to_address: str, selector: str, timeout: int = 10) -> str:
    """向 RPC 节点发一次 eth_call，返回原始 hex 字符串结果"""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": to_address, "data": selector}, "latest"],
        "id": 1,
    }
    resp = requests.post(rpc_url, json=payload, timeout=timeout)
    resp.raise_for_status()
    j = resp.json()
    if "error" in j:
        raise RpcError(str(j["error"]))
    result = j.get("result")
    if result is None:
        raise RpcError("RPC 返回结果为空，请检查地址/网络是否正确")
    return result


def _hex_to_bytes(hex_str: str) -> bytes:
    if hex_str.startswith("0x") or hex_str.startswith("0X"):
        hex_str = hex_str[2:]
    return bytes.fromhex(hex_str)


def decode_string(hex_result: str) -> str:
    """解码 ABI 编码的 string 类型返回值（动态类型：offset+length+data）"""
    data = _hex_to_bytes(hex_result)
    # data[0:32] 是 offset（单一返回值时固定是 0x20），跳过
    length = int.from_bytes(data[32:64], "big")
    str_bytes = data[64:64 + length]
    return str_bytes.decode("utf-8", errors="replace")


def get_reserves(rpc_url: str, pair_address: str):
    """返回 (reserve0, reserve1) 原始整数（未除以 decimals）"""
    result = eth_call(rpc_url, pair_address, SELECTOR_GET_RESERVES)
    data = _hex_to_bytes(result)
    reserve0 = int.from_bytes(data[0:32], "big")
    reserve1 = int.from_bytes(data[32:64], "big")
    return reserve0, reserve1


def get_decimals(rpc_url: str, token_address: str) -> int:
    result = eth_call(rpc_url, token_address, SELECTOR_DECIMALS)
    return int(result, 16)


def get_symbol(rpc_url: str, token_address: str) -> str:
    result = eth_call(rpc_url, token_address, SELECTOR_SYMBOL)
    return decode_string(result)


def to_checksum_lower(address: str) -> str:
    """这里不做真正的 EIP-55 checksum 编码，节点通常接受全小写地址；
    如果贵节点严格要求 checksum 地址，请直接在配置里填官方给的原始大小写地址。"""
    return address
