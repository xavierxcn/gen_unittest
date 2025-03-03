package com.example.usermanagement;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * 用户管理类，负责用户注册、登录和权限管理
 */
public class UserManager {
    private Map<String, User> users;
    private User currentUser;
    private DatabaseHelper dbHelper;
    
    /**
     * 构造函数
     * @param dbHelper 数据库帮助类
     */
    public UserManager(DatabaseHelper dbHelper) {
        this.users = new HashMap<>();
        this.dbHelper = dbHelper;
    }
    
    /**
     * 注册新用户
     * @param username 用户名
     * @param password 密码
     * @param email 电子邮件
     * @return 注册是否成功
     * @throws IllegalArgumentException 如果参数无效
     */
    public boolean registerUser(String username, String password, String email) {
        // 验证参数
        if (username == null || username.trim().isEmpty()) {
            throw new IllegalArgumentException("用户名不能为空");
        }
        
        if (password == null || password.length() < 6) {
            throw new IllegalArgumentException("密码长度必须至少为6个字符");
        }
        
        if (email == null || !isValidEmail(email)) {
            throw new IllegalArgumentException("电子邮件格式无效");
        }
        
        // 检查用户是否已存在
        if (users.containsKey(username)) {
            return false;
        }
        
        // 创建新用户
        User newUser = new User(username, password, email);
        users.put(username, newUser);
        
        // 保存到数据库
        return dbHelper.saveUser(newUser);
    }
    
    /**
     * 用户登录
     * @param username 用户名
     * @param password 密码
     * @return 登录是否成功
     */
    public boolean login(String username, String password) {
        if (username == null || password == null) {
            return false;
        }
        
        User user = users.get(username);
        if (user != null && user.getPassword().equals(password)) {
            currentUser = user;
            return true;
        }
        
        return false;
    }
    
    /**
     * 用户登出
     */
    public void logout() {
        currentUser = null;
    }
    
    /**
     * 获取当前登录用户
     * @return 当前用户，如果未登录则返回null
     */
    public User getCurrentUser() {
        return currentUser;
    }
    
    /**
     * 更新用户信息
     * @param username 用户名
     * @param newEmail 新电子邮件
     * @return 更新是否成功
     */
    public boolean updateUserEmail(String username, String newEmail) {
        if (username == null || newEmail == null || !isValidEmail(newEmail)) {
            return false;
        }
        
        User user = users.get(username);
        if (user != null) {
            user.setEmail(newEmail);
            return dbHelper.updateUser(user);
        }
        
        return false;
    }
    
    /**
     * 删除用户
     * @param username 要删除的用户名
     * @return 删除是否成功
     */
    public boolean deleteUser(String username) {
        if (username == null) {
            return false;
        }
        
        if (users.containsKey(username)) {
            users.remove(username);
            return dbHelper.deleteUser(username);
        }
        
        return false;
    }
    
    /**
     * 获取所有用户
     * @return 用户列表
     */
    public List<User> getAllUsers() {
        return new ArrayList<>(users.values());
    }
    
    /**
     * 验证电子邮件格式
     * @param email 要验证的电子邮件
     * @return 是否有效
     */
    private boolean isValidEmail(String email) {
        if (email == null) {
            return false;
        }
        
        String emailRegex = "^[a-zA-Z0-9_+&*-]+(?:\\.[a-zA-Z0-9_+&*-]+)*@(?:[a-zA-Z0-9-]+\\.)+[a-zA-Z]{2,7}$";
        Pattern pattern = Pattern.compile(emailRegex);
        return pattern.matcher(email).matches();
    }
    
    /**
     * 用户类
     */
    public static class User {
        private String username;
        private String password;
        private String email;
        private List<String> roles;
        
        public User(String username, String password, String email) {
            this.username = username;
            this.password = password;
            this.email = email;
            this.roles = new ArrayList<>();
        }
        
        public String getUsername() {
            return username;
        }
        
        public String getPassword() {
            return password;
        }
        
        public String getEmail() {
            return email;
        }
        
        public void setEmail(String email) {
            this.email = email;
        }
        
        public List<String> getRoles() {
            return roles;
        }
        
        public void addRole(String role) {
            if (role != null && !role.trim().isEmpty()) {
                roles.add(role);
            }
        }
        
        public boolean hasRole(String role) {
            return roles.contains(role);
        }
    }
    
    /**
     * 数据库帮助类接口
     */
    public interface DatabaseHelper {
        boolean saveUser(User user);
        boolean updateUser(User user);
        boolean deleteUser(String username);
        User getUser(String username);
    }
} 