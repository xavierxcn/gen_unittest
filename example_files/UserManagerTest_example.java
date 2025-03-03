package com.example.usermanagement;

import static org.junit.Assert.*;
import static org.mockito.Mockito.*;

import org.junit.Before;
import org.junit.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

public class UserManagerTest {
    
    @Mock
    private UserManager.DatabaseHelper dbHelper;
    
    private UserManager userManager;
    
    @Before
    public void setUp() {
        MockitoAnnotations.initMocks(this);
        userManager = new UserManager(dbHelper);
    }
    
    @Test
    public void testLogin_ValidCredentials_ReturnsTrue() {
        // 准备测试数据
        String username = "testuser";
        String password = "password123";
        
        // 模拟用户注册
        when(dbHelper.saveUser(any(UserManager.User.class))).thenReturn(true);
        userManager.registerUser(username, password, "test@example.com");
        
        // 执行测试
        boolean result = userManager.login(username, password);
        
        // 验证结果
        assertTrue("使用有效凭据登录应该成功", result);
        assertNotNull("登录后当前用户不应为空", userManager.getCurrentUser());
        assertEquals("当前用户名应匹配登录用户名", username, userManager.getCurrentUser().getUsername());
    }
} 