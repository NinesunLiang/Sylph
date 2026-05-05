### §A TDD Workflow

```
go// RED：先写失败测试func TestAdd(t *testing.T) { got := Add(2, 3) if got != 5 { t.Errorf("Add(2, 3) = %d; want 5", got) }}
// GREEN：最少实现func Add(a, b int) int { return a + b }
// REFACTOR：保持绿色，改善结构
```

### §B Table-Driven Tests

```
gofunc
TestParseConfig(t *testing.T) { tests := []struct { name string input string want *Config wantErr bool }{ { name: "合法配置", input: `{"host":"localhost","port":8080}`, want: \&Config{Host: "localhost", Port: 8080}, }, { name: "非法 JSON", input: `{invalid}`, wantErr: true, }, { name: "空输入", input: "", wantErr: true, }, { name: "最小配置", input: `{}`, want: \&Config{}, }, } for _, tt := range tests { t.Run(tt.name, func(t *testing.T) { // Go ≥ 1.22：无需 tt := tt got, err := ParseConfig(tt.input) if tt.wantErr { if err == nil { t.Error("期望 error，实际得到 nil") } return } if err != nil { t.Fatalf("意外 error: %v", err) } if !reflect.DeepEqual(got, tt.want) { t.Errorf("got %+v; want %+v", got, tt.want) } }) }}

```
