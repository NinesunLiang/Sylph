# §F Mocking & Interface Isolation

## Handwritten Mock

```
gotype mockRepo struct { getUserFunc func(id string) (*User, error)}
func (m *mockRepo) GetUser(id string) (*User, error) { return m.getUserFunc(id)}
```

## gomock Pattern

```
goctrl
:= gomock.NewController(t)repo := mock_repo.NewMockUserRepo(ctrl)repo.EXPECT().GetUser("123").Return(\&User{Name: "test"}, nil)

```

## testify/mock Pattern

```
gorepo
:= new(MockUserRepo)repo.On("GetUser", "123").Return(\&User{Name: "test"}, nil)defer repo.AssertExpectations(t)
```

## Strategy Selection

1. Check project's existing `*_test.go` for mock patterns
2. Match whatever the project uses
3. If no existing mocks: prefer handwritten for ≤3 methods, gomock/testify for more

## Rules

- Mock at interface boundary only
- Never mock concrete types
- Never mock standard library
- Verify expectations in test cleanup
- See `mock-strategy-quickref.md` for decision matrix
