import json


def compare_changes(before_data, after_data):
    """
    比较修改前后的数据，返回变更信息
    """
    changes = {}
    
    before_dict = before_data or {}
    after_dict = after_data or {}
    
    # 检查所有键
    all_keys = set(before_dict.keys()).union(set(after_dict.keys()))
    
    for key in all_keys:
        before_val = before_dict.get(key)
        after_val = after_dict.get(key)
        
        if before_val != after_val:
            changes[key] = {
                "before": before_val,
                "after": after_val
            }
    
    return changes


def format_changes_text(changes):
    """
    将变更信息格式化为文本
    """
    if not changes:
        return ""
    
    change_texts = []
    for key, val in changes.items():
        before = val.get("before")
        after = val.get("after")
        change_texts.append(f"{key}: {before} → {after}")
    
    return "; ".join(change_texts)
