# BIA entity relationship diagram

Source of truth: production/database.py. For an offline graphical view open BIA_ERD.html.

```mermaid
erDiagram
    direction TB
    currency_codes {
        string code PK
        string name
        int digits
    }
    departments {
        string id PK
        string name
        bool active
    }
    login_attempts {
        string key PK
        int count
        decimal expires
    }
    resources {
        string id PK
        string name
        bool active
    }
    roles {
        string code PK
        string name
    }
    schema_migrations {
        int version PK
        datetime appliedAt
    }
    vendors {
        string id PK
        string name
        bool active
    }
    workspace {
        int id PK
        int version
    }
    master_projects {
        string id PK
        string title
        string primaryDepartmentId FK
        string owner
        string description
    }
    users {
        string id PK
        string email
        string name
        string role FK
        string departmentId FK
        bool active
    }
    projects {
        string id PK
        string masterId FK
        string createdById FK
        string title
        string departmentId FK
        string owner
        decimal budget
        date start
        date due
        string description
        string color
    }
    sessions {
        string token PK
        string user_id FK
        decimal expires
    }
    user_credentials {
        string userId PK,FK
        string password_hash
    }
    audit_log {
        string id PK
        string projectId FK
        string actorId FK
        string actor
        string role
        string action
        datetime at
    }
    budget_change_requests {
        string id PK
        string projectId FK
        string title
        string reason
        decimal amount
        string status
        string requestedById FK
        string requestedBy
        date requestedDate
        string decidedById FK
        string decidedBy
        date decisionDate
        string decisionNote
        decimal budgetBefore
        decimal budgetAfter
    }
    project_baselines {
        string id PK
        string projectId FK
        int version
        string name
        string reason
        string createdById FK
        string createdBy
        datetime createdAt
        string title
        date start
        date due
    }
    project_days_off {
        string projectId PK,FK
        int weekday PK
    }
    project_department_access {
        string projectId PK,FK
        string groupId PK,FK
    }
    project_expenses {
        string id PK
        string projectId FK
        string kind
        date date
        string prNumber
        decimal amountJod
        string remarks
    }
    project_finance {
        string projectId PK,FK
        string currency FK
        decimal usdRate
        date rateDate
        string vendorId FK
    }
    purchase_orders {
        string id PK
        string projectId FK
        string number
        string vendorId FK
        decimal amount
        date date
        string description
    }
    tasks {
        string id PK
        string projectId FK
        string parentId FK
        string title
        string assigneeId FK
        string resourceId FK
        decimal effort
        date start
        date due
        int progress
        bool blocked
    }
    vendor_consultants {
        string id PK
        string vendorId FK
        string ownerProjectId FK
        string name
        bool active
    }
    baseline_tasks {
        string baselineId PK,FK
        string taskId PK,FK
        string parentId FK
        string title
        date start
        date due
        decimal effort
        bool isMilestone
    }
    consultant_details {
        string consultantId PK,FK
        string designation
    }
    consultant_trips {
        string id PK
        string projectId FK
        string consultantId FK
        date start
        date end
        bool biaFlight
        bool biaAccommodation
        bool biaFood
        string stayType
        bool flightBooked
        decimal flightCost
        date bookedDate
        string notes
    }
    invoices {
        string id PK
        string poId FK
        string number
        decimal amount
        date date
        date due
    }
    payment_terms {
        string id PK
        string projectId FK
        string title
        decimal amount
        string trigger
        date dueDate
        string milestoneId FK
        bool cancelled
    }
    progress_updates {
        string id PK
        string taskId FK
        int progress
        string note
        string authorId FK
        string author
        datetime createdAt
    }
    task_milestones {
        string taskId PK,FK
    }
    task_predecessors {
        string taskId PK,FK
        string predecessorId PK,FK
    }
    invoice_budget_changes {
        string invoiceId PK,FK
        string changeRequestId FK
    }
    invoice_payments {
        string invoiceId PK,FK
        string reference
        date paidDate
        string recordedById FK
    }
    invoice_terms {
        string invoiceId PK,FK
        string termId FK
    }
    trip_costs {
        string tripId PK,FK
        decimal flightCostJod
        string hotelBookedBy
        decimal hotelCostJod
        decimal visaCostJod
    }
    departments o|--o{ master_projects : "primaryDepartmentId"
    departments ||--o{ users : "departmentId"
    roles ||--o{ users : "role"
    users o|--o{ projects : "createdById"
    departments ||--o{ projects : "departmentId"
    master_projects ||--o{ projects : "masterId"
    users ||--o{ sessions : "user_id"
    users ||--o| user_credentials : "userId"
    users o|--o{ audit_log : "actorId"
    projects o|--o{ audit_log : "projectId"
    users o|--o{ budget_change_requests : "decidedById"
    projects ||--o{ budget_change_requests : "projectId"
    users ||--o{ budget_change_requests : "requestedById"
    users ||--o{ project_baselines : "createdById"
    projects ||--o{ project_baselines : "projectId"
    projects ||--o{ project_days_off : "projectId"
    departments ||--o{ project_department_access : "groupId"
    projects ||--o{ project_department_access : "projectId"
    projects ||--o{ project_expenses : "projectId"
    currency_codes ||--o{ project_finance : "currency"
    projects ||--o| project_finance : "projectId"
    vendors o|--o{ project_finance : "vendorId"
    projects ||--o{ purchase_orders : "projectId"
    vendors ||--o{ purchase_orders : "vendorId"
    users o|--o{ tasks : "assigneeId"
    tasks o|--o{ tasks : "parentId,projectId"
    projects ||--o{ tasks : "projectId"
    resources ||--o{ tasks : "resourceId"
    projects o|--o{ vendor_consultants : "ownerProjectId"
    vendors ||--o{ vendor_consultants : "vendorId"
    project_baselines ||--o{ baseline_tasks : "baselineId"
    tasks o|--o{ baseline_tasks : "parentId"
    tasks ||--o{ baseline_tasks : "taskId"
    vendor_consultants ||--o| consultant_details : "consultantId"
    vendor_consultants ||--o{ consultant_trips : "consultantId"
    projects ||--o{ consultant_trips : "projectId"
    purchase_orders ||--o{ invoices : "poId"
    projects ||--o{ payment_terms : "projectId"
    tasks o|--o{ payment_terms : "milestoneId,projectId"
    users o|--o{ progress_updates : "authorId"
    tasks ||--o{ progress_updates : "taskId"
    tasks ||--o| task_milestones : "taskId"
    tasks ||--o{ task_predecessors : "predecessorId"
    tasks ||--o{ task_predecessors : "taskId"
    budget_change_requests ||--o{ invoice_budget_changes : "changeRequestId"
    invoices ||--o| invoice_budget_changes : "invoiceId"
    invoices ||--o| invoice_payments : "invoiceId"
    users o|--o{ invoice_payments : "recordedById"
    invoices ||--o| invoice_terms : "invoiceId"
    payment_terms ||--o{ invoice_terms : "termId"
    consultant_trips ||--o| trip_costs : "tripId"
```
