def generate_direct_code(instruction: str, lang: str) -> str:
    """Generate actual usable code for simple coding tasks."""
    instruction_lower = instruction.lower()
    
    # Sorting - most specific first
    has_sort = any(w in instruction_lower for w in ["排序", "sort", "快排", "quicksort", "mergesort"])
    
    if has_sort:
        if "快" in instruction or "quick" in instruction_lower:
            if lang == "zh":
                return """```python
# 快速排序
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

nums = [3, 6, 8, 10, 1, 2, 1]
print(quicksort(nums))  # [1, 1, 2, 3, 6, 8, 10]
```

要点：
- 平均 O(n log n)，最坏 O(n^2)
- 选择中间元素作基准可减少最坏情况"""
        if "merge" in instruction_lower or "归并" in instruction:
            if lang == "zh":
                return """```python
# 归并排序
def mergesort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    return merge(mergesort(arr[:mid]), mergesort(arr[mid:]))

def merge(left, right):
    result = []
    while left and right:
        result.append(left.pop(0) if left[0] <= right[0] else right.pop(0))
    return result + left + right

nums = [3, 6, 8, 10, 1, 2, 1]
print(mergesort(nums))  # [1, 1, 2, 3, 6, 8, 10]
```

要点：
- 稳定排序，总是 O(n log n)
- 需要 O(n) 额外空间"""
        if lang == "zh":
            return """```python
# 排序函数
def sort_arr(arr, method="quick"):
    if method == "quick":
        return quicksort(arr)
    elif method == "merge":
        return mergesort(arr)
    return sorted(arr)

def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    return quicksort([x for x in arr if x < pivot]) + quicksort([x for x in arr if x == pivot]) + quicksort([x for x in arr if x > pivot])
```

支持: 快排(quick)、归并(merge)、内置排序(sorted)"""
    
    # Login
    if any(w in instruction_lower for w in ["登录", "login", "登陆"]):
        if lang == "zh":
            return """```python
# 用户登录函数
def login(username: str, password: str) -> dict:
    user = db.query("SELECT * FROM users WHERE username = ?", username)
    if not user:
        return {"success": False, "message": "用户不存在"}
    if not verify_password(password, user["password_hash"]):
        return {"success": False, "message": "密码错误"}
    return {"success": True, "user": {"id": user["id"], "username": user["username"]}}
```

要点：
- 使用密码哈希（不要存明文密码）
- SQL查询使用参数化防止注入
- 返回信息要模糊（不区分"用户不存在"和"密码错误"）"""
    
    # API
    if any(w in instruction_lower for w in ["api", "接口", "endpoint"]):
        if lang == "zh":
            return """```python
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/api/resource", methods=["GET"])
def get_resource():
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    resources = db.query("SELECT * FROM resources LIMIT ? OFFSET ?", (page-1)*limit, limit)
    total = db.query("SELECT COUNT(*) FROM resources")[0][0]
    return jsonify({"data": resources, "pagination": {"page": page, "limit": limit, "total": total}})
```"""
    
    # Generic
    if lang == "zh":
        topic = instruction.replace("帮我", "").replace("写", "").replace("一个", "").strip()
        func_name = ''.join(c for c in topic if c.isalnum() or c == '_')
        return f"""```python
# {topic}
def {func_name}():
    pass
```
提示: 较简单指令，请补充更多细节"""
    return f"""```python
# {instruction}
def process():
    pass
```"""
