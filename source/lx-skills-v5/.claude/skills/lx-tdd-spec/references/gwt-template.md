# GWT 场景模板（lx-tdd-spec）

## Given-When-Then 格式

```
场景：{描述} Given：{前置条件} When：{触发操作} Then：{期望结果}
```

## 示例（Go）

```
go// 场景：正常登录// Given: 手机号已注册，验证码正确// When: POST /api/login {"phone":"138xx","code":"1234"}// Then: 返回 200 + token
func TestLoginHandler_Success(t *testing.T) { // Given user := testutil.CreateUser(t, "13800000000") code := testutil.SetVerifyCode(t, user.Phone, "1234") // When resp := testutil.POST(t, "/api/login", map[string]string{ "phone": user.Phone, "code": code, }) // Then assert.Equal(t, 200, resp.Code) assert.NotEmpty(t, resp.Body["token"])}
```
