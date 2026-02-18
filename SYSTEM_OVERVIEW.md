# System Overview: Data Management & Sample Management

## 📊 Database Tables

### 1. **sample** Table (Core Sample Information)
**Purpose:** Stores physical sample metadata and property values

**Key Fields:**
```sql
- sample_id (INT, PRIMARY KEY, AUTO_INCREMENT)
- sample_name (VARCHAR) - Sample identifier (e.g., "wheat", "10no060126")
- model_num (INT) - Number of scans/quantity
- model_wavemin (FLOAT) - Minimum wavelength (e.g., 900)
- model_wavemax (FLOAT) - Maximum wavelength (e.g., 1700)
- model_wavepath (FLOAT) - Wavelength step size (e.g., 1)
- model_method (INT) - Scanning method (0/1/2)
- sample_status (VARCHAR) - '0'=Not collected, '1'=Collected
- sample_state (VARCHAR) - NULL or 'Deleted'
- property_name1 to property_name10 (VARCHAR) - Property IDs (FK to content_dictionary)
- property_value1 to property_value10 (VARCHAR) - Property values (e.g., "12.5")
- create_person (VARCHAR) - User ID
- create_time (DATETIME) - Sample creation timestamp
```

**Usage:**
- Stores sample configuration and reference values
- Linked to model_data for spectral data
- Used for modify/delete operations
- Property values store substance content (protein, moisture, etc.)

---

### 2. **model_data** Table (Spectral Data Storage)
**Purpose:** Stores actual spectral scan data for each import

**Key Fields:**
```sql
- model_id (INT, PRIMARY KEY, AUTO_INCREMENT)
- sample_id (INT, FOREIGN KEY → sample.sample_id)
- device_id (VARCHAR) - Instrument identifier (e.g., "5100", "AG9170")
- model_sno (VARCHAR) - Lot/serial number
- wave (TEXT) - Comma-separated wavelengths: "900,901,902,...,1700"
- absorb (TEXT) - Comma-separated absorbance values: "0.123,0.145,..."
- create_time (DATETIME) - Import timestamp
```

**Usage:**
- One row per import/scan
- Links to sample table via sample_id
- Multiple model_data rows can share same sample_id (replicates)
- Used for grouping by import time
- Spectral data stored as CSV strings

**Relationship:**
```
sample (1) ←→ (N) model_data
One sample can have multiple spectral imports
```

---

### 3. **content_dictionary** Table (Property Definitions)
**Purpose:** Master list of measurable properties

**Key Fields:**
```sql
- id (INT, PRIMARY KEY, AUTO_INCREMENT)
- content_name (VARCHAR) - Property name (e.g., "Protein", "Moisture", "Oil")
```

**Usage:**
- Dynamically loaded in UI dropdowns
- Referenced by sample.property_name1-10
- Auto-populated when importing CSV with new properties
- Used for batch import matching

---

### 4. **project** Table (Calibration Projects)
**Purpose:** Groups samples for calibration model building

**Key Fields:**
```sql
- project_id (INT, PRIMARY KEY, AUTO_INCREMENT)
- project_name (VARCHAR) - Project identifier
- sample_type (VARCHAR) - Granules/Powder/Liquid
- measurement_type (VARCHAR) - Qualitative/Quantitative
- measurement_index (TEXT) - Comma-separated property names
- remark (VARCHAR) - Notes
- create_person (VARCHAR) - User ID
- create_time (DATETIME) - Project creation time
```

---

### 5. **project_sample** Table (Project-Sample Junction)
**Purpose:** Many-to-many relationship between projects and samples

**Key Fields:**
```sql
- id (INT, PRIMARY KEY, AUTO_INCREMENT)
- project_id (INT, FOREIGN KEY → project.project_id)
- sample_id (INT, FOREIGN KEY → sample.sample_id)
```

**Relationship:**
```
project (1) ←→ (N) project_sample (N) ←→ (1) sample
Many projects can contain many samples
```

---

## 🔄 Data Flow Architecture

### **1. DATA IMPORT FLOW**

#### **Entry Points:**
- **Sample Management:** "Add" button → Data Import Dialog
- **Data Management:** "Import" button → Data Import Dialog

#### **Import Process:**
```
User Action:
├─ Select mode: "file" or "folder"
├─ Choose files/folder
├─ Set separator (e.g., "_")
├─ Select instrument (optional)
└─ Click OK

↓

import_spectral_files() [ui/sample_management.py]
├─ Parse each CSV file
│  ├─ Extract wavelength + absorbance columns
│  └─ Extract sample name from filename/folder
│
├─ Determine sample_name
│  ├─ File mode: filename (without extension)
│  └─ Folder mode: parent folder name
│
├─ Extract lot number using separator
│  └─ "ABC_sample1.csv" with "_" → lot = "ABC"
│
├─ Check if sample exists in database
│  ├─ EXISTS: Get sample_id
│  └─ NEW: INSERT into sample table
│     └─ Calculate min/max/step from wavelengths
│
├─ INSERT into model_data table
│  ├─ sample_id (FK)
│  ├─ device_id (instrument)
│  ├─ model_sno (lot number)
│  ├─ wave (comma-separated wavelengths)
│  ├─ absorb (comma-separated absorbance)
│  └─ create_time (NOW)
│
└─ Commit transaction
```

#### **Database Operations:**
```sql
-- Check existing sample
SELECT sample_id FROM sample WHERE sample_name = 'wheat'

-- Insert new sample (if not exists)
INSERT INTO sample (
    sample_name, model_num, model_wavemin, model_wavemax,
    model_wavepath, model_method, sample_status,
    create_person, create_time
) VALUES ('wheat', 1, 900, 1700, 1, 0, '0', 'user', NOW())

-- Insert spectral data (always new row)
INSERT INTO model_data (
    sample_id, device_id, model_sno, wave, absorb, create_time
) VALUES (38, '5100', 'ABC', '900,901,902,...', '0.123,0.145,...', NOW())
```

---

### **2. INQUIRY FLOW (Display Samples)**

#### **User Action:**
```
Sample Management → Set date range → Click "Inquiry"
```

#### **Backend Process:**
```
on_inquiry_clicked() [ui/sample_management.py]
├─ Get date filters (date_from, date_to)
│
├─ Call SampleService.get_samples_by_date()
│  │
│  └─ Execute SQL:
│     SELECT 
│         md.model_id as id,           -- Import ID
│         s.sample_name,
│         s.model_num,
│         md.create_time,              -- Import timestamp
│         s.sample_id                  -- Physical sample ID
│     FROM model_data md
│     INNER JOIN sample s ON md.sample_id = s.sample_id
│     WHERE DATE(md.create_time) BETWEEN ? AND ?
│     ORDER BY md.create_time DESC
│
├─ Group samples by (sample_name, creation_time_minute)
│  │
│  ├─ Truncate time to minute: "2026-02-10 17:34:31" → "2026-02-10 17:34"
│  │
│  ├─ Create group_key = (sample_name, time_minute)
│  │
│  └─ For each group:
│     ├─ Store first model_id as group ID
│     ├─ Store all sample_ids in sample_ids[]
│     ├─ Store all model_ids in model_ids[]
│     ├─ Sum scanned_number
│     └─ Merge substance_content (prefer longer)
│
├─ Sort by creation_time DESC (newest first)
│
└─ Populate table with merged groups
```

#### **Table Display:**
```
ID (model_id) | Sample Name | Quantity | Scanned | Creation Time
4549          | wheat       | 0        | 3       | 2026-02-10 17:34
4546          | 10no060126  | 0        | 3       | 2026-02-10 17:34
4543          | 10no050126  | 0        | 3       | 2026-02-10 17:34
```

**Notes:**
- ID = model_id (stable database ID)
- Scanned = sum of all scans in that minute
- Multiple imports within same minute are merged

---

### **3. BATCH IMPORT SUBSTANCE CONTENT**

#### **Flow:**
```
User Action:
├─ Tick samples in table
├─ Click "Template Download"
│  ├─ Generates CSV with:
│  │  └─ sample ID (model_id) | sample name | protein | moisture | ...
│  └─ User fills in values
│
└─ Click "Batch Import"
   └─ Upload filled CSV

↓

batch_import_substance_content() [services/sample_service.py]
├─ Read CSV file
│
├─ For each row:
│  ├─ Extract model_id (from "sample ID" column)
│  ├─ Extract sample_name (from "sample name" column)
│  │
│  ├─ Find matching samples:
│  │  SELECT s.sample_id
│  │  FROM sample s
│  │  INNER JOIN model_data md ON s.sample_id = md.sample_id
│  │  WHERE md.model_id = ? AND s.sample_name = ?
│  │
│  ├─ Filter by selected_sample_ids (only ticked ones)
│  │
│  └─ Update sample properties:
│     UPDATE sample
│     SET property_name1 = ?, property_value1 = ?, ...
│     WHERE sample_id IN (...)
│
└─ Commit transaction
```

#### **Key Logic:**
- **Matching:** Uses (model_id + sample_name) combination
- **Precision:** Only updates specific import, not all samples with same name
- **Safety:** Only updates ticked samples

---

### **4. SAMPLE STORAGE MECHANISM**

#### **Storage Model:**
```
Physical Sample "wheat":
├─ sample table (1 row)
│  ├─ sample_id: 38
│  ├─ sample_name: "wheat"
│  ├─ property_value1: "12.5" (Protein)
│  ├─ property_value2: "10.2" (Moisture)
│  └─ ...
│
└─ model_data table (multiple rows = multiple imports)
   ├─ Import 1 (model_id: 4549)
   │  ├─ sample_id: 38
   │  ├─ create_time: 2026-02-10 17:34:30
   │  ├─ wave: "900,901,902,..."
   │  └─ absorb: "0.123,0.145,..."
   │
   ├─ Import 2 (model_id: 4548)
   │  ├─ sample_id: 38
   │  ├─ create_time: 2026-02-10 17:34:31
   │  └─ ...
   │
   └─ Import 3 (model_id: 4547)
      └─ ...
```

**Design Pattern:**
- **Sample Table:** Reference data (what to measure)
- **Model_Data Table:** Time-series data (spectral scans)
- **One-to-Many:** One sample → Multiple imports

---

### **5. DISPLAY LOGIC**

#### **UI Grouping Strategy:**
```python
# Group by (sample_name, creation_time_up_to_minute)
group_key = (sample_name, creation_time[:16])

# Example:
("wheat", "2026-02-10 17:34") → Group 1
  ├─ model_id: 4549 (17:34:30)
  ├─ model_id: 4548 (17:34:31)
  └─ model_id: 4547 (17:34:32)

("wheat", "2026-02-10 17:35") → Group 2
  └─ model_id: 4546 (17:35:10)
```

#### **Benefits:**
✅ Samples scanned in same batch appear as one row
✅ Different import times show separately
✅ User sees logical grouping
✅ Precise selection for operations

---

## 🔧 Key Operations

### **Modify Sample**
```
User ticks 1 row → Modify button
├─ Get model_id from row
├─ Find sample_ids from merged_samples
├─ Call get_sample_by_id(sample_id[0])
├─ Open modify dialog
└─ UPDATE sample table (properties only)
```

### **Delete Sample**
```
User ticks rows → Delete button
├─ Get all sample_ids from ticked groups
├─ Check if has spectral data (model_data)
│  └─ If YES: Block deletion (warn user)
├─ DELETE FROM sample WHERE sample_id IN (...)
└─ CASCADE: model_data auto-deleted (if FK set)
```

### **Template Download**
```
User ticks rows → Template Download
├─ Get sample_ids from ticked groups
├─ Query sample table for properties
├─ Replace sample_id with model_id in CSV
└─ Export: model_id | sample_name | protein | moisture | ...
```

---

## 📋 Summary Table

| Feature | Sample Management | Data Management |
|---------|------------------|----------------|
| **Primary Function** | Manage samples & properties | View/analyze spectral data |
| **Import** | Via "Add" → Import Dialog | Via "Import" button |
| **Display** | Grouped by (name + time) | Raw spectral plots |
| **Edit** | Modify properties | View-only |
| **Delete** | Delete samples | N/A |
| **Export** | Template with properties | Export spectral data |

---

## 🔑 Key Differences

### **Sample Management:**
- **Focus:** Sample metadata and substance content
- **Grouping:** By (sample_name, import_minute)
- **ID Displayed:** model_id (stable)
- **Operations:** Add, Modify, Delete, Import properties

### **Data Management:**
- **Focus:** Spectral data visualization
- **Grouping:** By sample_name only (all imports merged)
- **ID Displayed:** Auto-increment (1, 2, 3...)
- **Operations:** View plots, Export data, Import scans

---

## 📊 Database Relationships Diagram

```
┌─────────────────────┐
│  content_dictionary │
│  ─────────────────  │
│  id (PK)           │
│  content_name      │ (Protein, Moisture, Oil...)
└──────────┬──────────┘
           │ Referenced by
           │ property_name1-10
           ↓
┌─────────────────────┐         ┌──────────────────┐
│      sample         │←────────│   model_data     │
│  ─────────────────  │ 1:N     │  ──────────────  │
│  sample_id (PK)    │         │  model_id (PK)   │
│  sample_name       │         │  sample_id (FK)  │
│  property_name1-10 │         │  device_id       │
│  property_value1-10│         │  wave (TEXT)     │
│  create_time       │         │  absorb (TEXT)   │
└──────────┬──────────┘         │  create_time     │
           │                     └──────────────────┘
           │ Referenced by              ↑
           │ project_sample             │ One import
           ↓                             │ per scan
┌─────────────────────┐                 │
│  project_sample     │                 │
│  ─────────────────  │                 │
│  id (PK)           │                 │
│  project_id (FK)   │──┐              │
│  sample_id (FK)    │  │              │
└─────────────────────┘  │              │
                          │              │
┌─────────────────────┐  │              │
│      project        │←─┘              │
│  ─────────────────  │                 │
│  project_id (PK)   │                 │
│  project_name      │                 │
│  measurement_index │                 │
└─────────────────────┘                 │
                                         │
                         (create_time used for grouping)
```

---

This document provides a complete overview of how data flows through the system, from import to storage to display.
