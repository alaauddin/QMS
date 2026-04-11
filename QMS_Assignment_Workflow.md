# 🏗️ Queue Management System – Assignment Workflow Documentation

This document describes the robust workflow for assigning operators to counters, ensuring data integrity and session management.

---

## 1. **Assignment Lifecycle**

### **Step 1: Authentication**
Operators log in using standard credentials. Upon successful login, they are directed to the **Counter Selection** page.

### **Step 2: Selection & Activation**
- The operator chooses a **Service** and an available **Counter**.
- A `CounterAssignment` is created/updated with `is_active=True`.
- **Constraint**: Any previous active assignment for the same user is automatically deactivated (`is_active=False`, `end_time=now`).

### **Step 3: Operation**
The operator proceeds to their dashboard. If they attempt to access it without an active assignment, they are redirected back to the selection page.

### **Step 4: Termination**
The assignment remains active until:
1. The operator logs out (triggers manual deactivation).
2. The operator selects a different counter (triggers auto-deactivation).
3. The shift-activation management command deactivates it based on scheduled hours.

---

## 2. **Technical Safeguards**

### **Model Logic**
The `CounterAssignment` model includes a customized `save()` method or signal handler to ensure that `is_active=True` is unique per user at any given time.

### **Session Management**
- **Manual Logout**: A custom logout view ensures the `end_time` is recorded.
- **Audit Trail**: Every assignment is preserved for historical reporting, with `deactivated` status and `end_time` distinguishing past sessions.
