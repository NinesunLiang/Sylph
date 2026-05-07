# §I HTTP Handler Tests

## Pattern

```gofu
n
c TestHandler(t *testing.T) { // Setup svc := \&mockService{...} handler := NewHandler(svc)
 tests := []struct { name string method string path string body string wantStatus int wantBody string }{ {"GET success", "GET", "/users/1", "", 200, `{"id":"1"}`}, {"POST invalid", "POST", "/users", `{}`, 400, ""}, {"not found", "GET", "/users/999", "", 404, ""}, } for _, tt := range tests { t.Run(tt.name, func(t *testing.T) { req := httptest.NewRequest(tt.method, tt.path, strings.NewReader(tt.body)) rec := httptest.NewRecorder()
 handler.ServeHTTP(rec, req)
 if rec.Code != tt.wantStatus { t.Errorf("status = %d, want %d", rec.Code, tt.wantStatus) } if tt.wantBody != "" { got := strings.TrimSpace(rec.Body.String()) if got != tt.wantBody { t.Errorf("body = %s, want %s", got, tt.wantBody) } } }) }}
```

## Rules- Use `httptest.NewRequest` + `httptest.NewRecorder`- Mock service layer, not HTTP client- Test status code + response body + headers- Test middleware separately from handlers- For authentication: test both authed and unauthed- Never start real HTTP server for unit tests
