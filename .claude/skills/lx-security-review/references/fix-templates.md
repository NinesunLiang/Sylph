# Go Security Fix Templates (§A-§J)

## §A: Hardcoded Key → Environment Variable

```g
o
// BEFOREapiKey := "sk-live-abc123def456..."
// AFTERapiKey := os.Getenv("API_KEY")if apiKey == "" { log.Fatal("API_KEY environment variable is required")}
```Als
o
: confirm `.gitignore` includes `.env`

## §B: SQL Injection → Parameterized Query

```g
o
// BEFOREquery := fmt.Sprintf("SELECT * FROM users WHERE id = '%s'", userID)rows, err := db.Query(query)
// AFTERrows, err := db.QueryContext(ctx, "SELECT * FROM users WHERE id = ?", userID)
```

## §C: Command Injection → Argument List

```g
o
// BEFOREcmd := exec.Command("sh", "-c", "convert " + userInput)
// AFTERcmd := exec.Command("convert", arg1, arg2) // no string concatenation
```

## §D: Path Traversal → Clean + Prefix Validation

```g
o
// AFTERcleanPath := filepath.Clean(userPath)if !strings.HasPrefix(cleanPath, allowedDir) { http.Error(w, "forbidden", http.StatusForbidden) return}
go// AFTERcleanPath := filepath.Clean(userPath)if !strings.HasPrefix(cleanPath, allowedDir) { http.Error(w, "forbidden", http.StatusForbidden) return}

```

## §E: Sensitive Data in Logs → Remove Sensitive Fields

```g
o
// BEFORElog.Printf("user login: %s, password: %s", user, password)
// AFTERlog.Printf("user login: userID=%s, action=login, time=%s", user.ID, time.Now())
```

## §F: Missing Input Validation → Add Validation + 400

```g
o
// AFTERvalue := r.FormValue("email")if len(value) == 0 || len(value) > 255 || !isValidEmail(value) { http.Error(w, "invalid input", http.StatusBadRequest) return}
go// AFTERvalue := r.FormValue("email")if len(value) == 0 || len(value) > 255 || !isValidEmail(value) { http.Error(w, "invalid input", http.StatusBadRequest) return}
```

## §G: Error Message Leak → Log Internal, Generic Client Message

```g
o
// BEFOREhttp.Error(w, err.Error(), http.StatusInternalServerError)
// AFTERlog.Printf("internal error: %v", err)http.Error(w, "internal server error", http.StatusInternalServerError)
```

## §H: Missing Authorization → Context User + Ownership Check

```g
o
// AFTERuser := auth.UserFromContext(r.Context()) // reuse project's auth helperif user == nil || !user.CanAccess(resource) { http.Error(w, "forbidden", http.StatusForbidden) return}
go// AFTERuser := auth.UserFromContext(r.Context()) // reuse project's auth helperif user == nil || !user.CanAccess(resource) { http.Error(w, "forbidden", http.StatusForbidden) return}

```

## §I: SSRF → URL Whitelist + Block Internal IPs

```g
o
// BEFOREresp, err := http.Get(r.FormValue("url"))
// AFTERimport "net/url"
targetURL := r.FormValue("url")parsed, err := url.Parse(targetURL)if err != nil { http.Error(w, "invalid URL", http.StatusBadRequest) return}
// Block internal IPs and private networksallowedHosts := map[string]bool{"api.example.com": true, "cdn.example.com": true}if !allowedHosts[parsed.Hostname()] { http.Error(w, "forbidden host", http.StatusForbidden) return}
// Use custom client with timeout, no redirects to internalclient := \&http.Client{ Timeout: 10 * time.Second, CheckRedirect: func(req *http.Request, via []*http.Request) error { if !allowedHosts[req.URL.Hostname()] { return fmt.Errorf("redirect to forbidden host: %s", req.URL.Hostname()) } return nil },}resp, err := client.Get(parsed.String())
```

## §J: http.DefaultClient → Custom Client with Timeout

```g
o
// BEFOREresp, err := http.DefaultClient.Get(url)
// AFTERclient := \&http.Client{Timeout: 10 * time.Second}resp, err := client.Get(url)
```
