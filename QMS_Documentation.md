# 📄 Queue Management System – Detailed Documentation

## 1. **System Overview**

The Queue Management System (QMS) is designed to manage customer service efficiently using a ticket-based workflow. It provides:

* **Customer interaction** via a kiosk to take tickets
* **Counter operation** for employees to call and process tickets
* **Display screens** above counters to show current tokens in real-time
* **Shift management** and multiple operators per counter
* **Real-time updates** using WebSocket technology

**Key Features:**

* Token issuance for multiple services
* Real-time screen updates
* Multi-user support for counters
* Shift management
* Sound announcements for called tokens
* Dashboard for administrators to monitor counters and tickets

---

## 2. **System Architecture**

```
+-------------------+          +-----------------+         +--------------------+
| Customer Kiosk    |  <---->  | Django Backend  |  <----> | Counter Display    |
| (Ticket Machine)  |          | (Web + API)     |         | (Screen Browser)   |
+-------------------+          +-----------------+         +--------------------+
                                    |
                                    |
                                    v
                             +----------------+
                             | Database (DB)  |
                             | PostgreSQL/MySQL|
                             +----------------+
                                    |
                                    v
                             +----------------+
                             | Redis (Optional)|
                             | WebSocket Hub  |
                             +----------------+
```

**Explanation:**

1. **Customer Kiosk:** Customers take a token for the service they need. Can be a touchscreen or web kiosk.
2. **Django Backend:** Handles token generation, counter assignment, employee login, and API for screens.
3. **Counter Screens:** Show tokens in real-time. Connected via WebSockets.
4. **Database:** Stores all tokens, counters, users, and screens.
5. **Redis (Optional):** Used for fast WebSocket messaging (recommended with Django Channels).

---

## 3. **Models and Relationships**

### 3.1 Service

```python
class Service(models.Model):
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=5)

    def __str__(self):
        return self.name
```

* Each service has a **prefix** for token numbers (e.g., “A” for Cashier, “B” for Customer Support)
* Can be extended to multiple services

---

### 3.2 Counter

```python
class Counter(models.Model):
    number = models.IntegerField()
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    def __str__(self):
        return f"Counter {self.number}"
```

* Counters are linked to services
* Multiple counters can exist per service

---

### 3.3 CounterAssignment (Shift & Multi-user Support)

```python
class CounterAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    counter = models.ForeignKey(Counter, on_delete=models.CASCADE)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'counter')
```

* Assigns **users to counters**
* Supports **multiple users per counter**
* Supports **shifts** using `start_time` / `end_time`
* `is_active` flag indicates who is currently operating the counter

---

### 3.4 Token

```python
class Token(models.Model):
    number = models.IntegerField()
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('called', 'Called'),
        ('done', 'Done'),
        ('skipped', 'Skipped'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    counter = models.ForeignKey(Counter, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.service.prefix}{self.number}"
```

* Tracks the token status
* Links tokens to counters when called
* Allows filtering for real-time queue display

---

### 3.5 Screen

```python
class Screen(models.Model):
    name = models.CharField(max_length=50)
    counter = models.ForeignKey(Counter, on_delete=models.CASCADE)
    device_token = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Screen for Counter {self.counter.number}"
```

* Each counter can have a screen (or multiple screens)
* Screens are identified using `device_token` for secure direct access
* Supports plug & play functionality

---

## 4. **Workflows**

### 4.1 Customer Token Workflow

1. Customer selects a **service** at the kiosk
2. System generates a **new token**:

   * Number auto-incremented
   * Linked to the service
   * Status = `waiting`
3. Ticket is printed or displayed on screen

---

### 4.2 Employee / Counter Workflow

1. Employee logs in → selects **counter** (or auto-assigned via `CounterAssignment`)
2. Employee clicks **Next**:

   * System finds next waiting token
   * Assigns token to counter
   * Updates token status → `called`
   * Sends update to screen (via WebSocket)
3. Screen displays token in real-time
4. Optional: Employee can **Recall / Skip / Done**

---

### 4.3 Screen Display Workflow

* Screens open the URL:

```
/screen/<device_token>/
```

* Connects via WebSocket to Django backend
* Receives **real-time token updates**
* Optional **audio announcements** using `speechSynthesis` API

---

### 4.4 Shift Management Workflow

1. Admin assigns users to counters using `CounterAssignment`
2. System automatically activates the user during their shift (`is_active = True`)
3. Only **one active user per counter** at any time
4. Multiple users can rotate across shifts

---

## 5. **Real-Time Implementation**

* Use **Django Channels** + Redis
* WebSocket Groups per Counter:

```
group_name = f"counter_{counter.id}"
```

* Push updates when employee calls **Next**:

```python
async_to_sync(channel_layer.group_send)(
    f"counter_{counter.id}",
    {
        "type": "token_called",
        "token": token.number,
        "service": token.service.prefix
    }
)
```

---

## 6. **Frontend UI Suggestions**

### 6.1 Counter Dashboard (Employee)

* Display:

  * Current token
  * Next button
  * Recall / Skip / Done
* Big buttons for touchscreens
* Responsive layout

---

### 6.2 Screen Display (Public Screen)

* Display:

  * Current token number
  * Counter number
* Optional: animation & sound
* Full screen (no browser navigation)

---

### 6.3 Customer Kiosk UI

* Touch-friendly
* Select service → Get token
* Optional: ticket printing

---

## 7. **Technical Notes**

1. **Database Indexing**

   * Index tokens by `status` and `counter` for fast queries
2. **Security**

   * Screen URL uses `device_token`
   * Only authenticated employees can call tokens
3. **Scalability**

   * Supports multiple counters & screens
   * Can handle thousands of tokens per day
4. **Deployment**

   * Use `gunicorn` + `nginx`
   * Redis for Channels
   * Optional SSL for secure connections

---

## 8. **Optional Features**

* Voice announcement for tokens
* Display main lobby screen with **all counters & tokens**
* Analytics: average waiting time, tokens per service
* Multi-language support (Arabic, English)

---

## 9. **Summary of Model Relations**

```
Service
   └─ Counter
         └─ CounterAssignment ── User
         └─ Token ── Service
         └─ Screen
```

* CounterAssignment handles **multi-user & shift logic**
* Token handles **queue & status**
* Screen handles **real-time display**
