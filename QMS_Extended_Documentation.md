# 🏗️ Queue Management System – Extended Project Documentation

This document complements the initial documentation with details for the customer kiosk, automatic shift management, and administrative dashboards.

---

## 1. **Customer Kiosk (Ticket Issuance)**

The Kiosk is the primary interaction point for customers. It allows them to select a service and receive a printed token.

### **Workflow:**
1. Customer views available services on a touchscreen.
2. Customer taps a service (e.g., "Cashier").
3. System creates a `Token` record with status `waiting`.
4. System displays a "Print" view which triggers the browser print dialog.

---

## 2. **Shift Auto-Activation**

To avoid manual status updates for operators, we use a management command that checks if the current time falls within a `CounterAssignment`'s shift window.

### **Command Details:**
- Checks `start_time` and `end_time` for all assignments.
- Sets `is_active = True` if `start_time <= now <= end_time`.
- Can be scheduled via Cron or Celery.

---

## 3. **Administrative Dashboard**

A high-level overview for managers to monitor the queue status in real-time.

### **Features:**
- List of all counters and their current services.
- Real-time list of the last 50 tokens and their statuses.
- Status overview of all operators (who is currently active).

---

## 4. **Localization (Arabic & RTL)**

All interfaces are designed with RTL (Right-to-Left) support using:
- HTML `dir="rtl"` attribute.
- Arabic translations for all text and messages.
- Bootstrap RTL and logical CSS properties for mirroring.

---

## 5. **Technical Implementation Details**

### **New Views:**
- `kiosk`: Lists services.
- `take_token`: Logic for token generation.
- `admin_dashboard`: Logic for system-wide monitoring.

### **New Command:**
- `activate_shifts`: Periodic task for shift management.
