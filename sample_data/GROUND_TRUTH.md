# Ground Truth Benchmarks for Sample Data

Seeded with deterministic pseudo-random seed `42`.

## 1. Core Summary Metrics
- **Total Orders**: 4,959 orders spanning 2023-01-01 to 2024-12-31 (24 months).
- **Total Customers**: 1,000 customers across North America (45%), EMEA (25%), APAC (20%), LATAM (10%).
- **Total Products**: 50 products across Hardware, Software, Cloud Services, Peripherals.

## 2. Seeded Key Insights
1. **Top Region by Revenue**:
   - **North America** leads total revenue across the 24-month horizon.
2. **Seeded Anomaly - March 2024 EMEA Revenue Dip**:
   - EMEA sales orders intentionally drop by ~65% in March 2024 to simulate a regional supply chain outage.
3. **Seeded Outliers (5 Giant Orders)**:
   - `ORD-OUT-01`: 2024-05-15, Qty 500, Unit Price $12,500.00 (Total: $6,250,000.00)
   - `ORD-OUT-02`: 2024-06-20, Qty 450, Unit Price $9,800.00 (Total: $4,189,500.00)
   - `ORD-OUT-03`: 2024-08-11, Qty 600, Unit Price $11,200.00 (Total: $6,720,000.00)
   - `ORD-OUT-04`: 2024-09-02, Qty 400, Unit Price $8,900.00 (Total: $3,204,000.00)
   - `ORD-OUT-05`: 2024-11-28, Qty 550, Unit Price $14,000.00 (Total: $7,700,000.00)
4. **Duplicate Block**:
   - 3 consecutive duplicated orders at index 10, 11, 12 appended at end of dataset.
5. **Nulls**:
   - Rows 15 to 20 contain NULL discount values for data quality auditing tests.
