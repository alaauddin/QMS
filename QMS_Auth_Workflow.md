# 🔐 QMS – Authentication & Assignment Workflow

This document details the secure login and counter assignment process for QMS operators.

---

## 1. **Authentication Flow**

### **Login Interface**
- Operators access the system via `/qms/login/`.
- The interface is fully RTL-compatible and optimized for Arabic and English.

### **Redirection Logic**
- Upon successful login, operators are redirected to the **Counter Selection** page.
- `LOGIN_URL` and `LOGIN_REDIRECT_URL` are configured in `settings.py`.

---

## 2. **Assignment Workflow**

### **Counter Selection**
- Operators select their **Service** and then an available **Counter**.
- Selecting a counter triggers the creation of a `CounterAssignment`.

### **Automatic Session Control**
- Creating a new active assignment automatically deactivates any existing sessions for that user.
- This ensures data consistency and prevents one user from hijacking multiple counters.

### **Logout & Deactivation**
- A custom logout view (`logout_counter_user`) is used.
- Before clearing the session, the system marks the current assignment as inactive and records the `end_time`.

---

## 3. **UI/UX Guidelines**
- **Modern Design**: Clean, card-based selection for counters.
- **RTL Support**: Cairo font and right-to-left layout for all Arabic speakers.
- **Feedback**: Clear error messages on the login page for failed authentication.
