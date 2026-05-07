# §F Mocking & Interface Isolation

## Handwritten Mock

```goty
p
e mockRepo struct { getUserFunc func(id string) (*User, error)}
func (m *mockRepo) GetUser(id string) (*User, error) { return m.getUserFunc(id)}
```

## gomock Pattern

```goct
r
l
:= gomock.NewController(t)repo := mock_repo.NewMockUserRepo(ctrl)repo.EXPECT().GetUser("123").Return(\&User{Name: "test"}, nil)

```

## testify/mock Pattern

```gore
p
o
:= new(MockUserRepo)repo.On("GetUser", "123").Return(\&User{Name: "test"}, nil)defer repo.AssertExpectations(t)
```

## Strategy Selection1. Check project's existing `*_test.go` for mock patterns2. Match whatever the project uses3. If no existing mocks: prefer handwritten for ≤3 methods, gomock/testify for more

## Rules- Mock at interface boundary only- Never mock concrete types- Never mock standard library- Verify expectations in test cleanup- See `mock-strategy-quickref.md` for decision matrix
