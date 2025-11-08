class ContextStateManager:
    """通用的上下文状态管理器，负责跟踪跨行的状态信息"""
    
    def __init__(self, initial_states=None):
        """
        初始化状态管理器
        
        参数:
            initial_states: 初始状态字典，格式为 {状态名: 初始值}
        """
        self.states = {}
        if initial_states:
            self.states = initial_states.copy()
    
    def reset(self, new_states=None):
        """重置所有状态"""
        self.states = {}
        if new_states:
            self.states = new_states.copy()
    
    def get(self, key, default=None):
        """获取状态值"""
        return self.states.get(key, default)
    
    def set(self, key, value):
        """设置状态值"""
        self.states[key] = value
    
    def has_changed(self, key, new_value):
        """检查状态是否发生变化"""
        old_value = self.get(key)
        return old_value != new_value
    
    def update_if_changed(self, key, new_value):
        """如果状态发生变化则更新并返回True，否则返回False"""
        if self.has_changed(key, new_value):
            self.set(key, new_value)
            return True
        return False
    
    def add_state(self, key, initial_value=None):
        """添加一个新的状态跟踪"""
        if key not in self.states:
            self.states[key] = initial_value
    
    def remove_state(self, key):
        """移除一个状态跟踪"""
        if key in self.states:
            del self.states[key]
    
    def get_all_states(self):
        """获取所有状态"""
        return self.states.copy()