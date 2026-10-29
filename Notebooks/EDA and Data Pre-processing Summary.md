# EDA and Data Pre-processing Summary
## 1. Exploratory Data Analysis (EDA)

I explored the Online Retail II dataset, which has about 1.07 million rows of retailer transactions from 2009 to 2011.

- Checked the structure and data types, and counted unique values in each column.
- Found missing values: Customer ID is missing in about 23% of rows, and Description in less than 1%.
- Found 34,335 exact duplicate rows (about 3%).
- Looked at Quantity and Price: both are heavily skewed, with many zero or negative values and extreme outliers.
- Charted the top countries (the UK dominates) and the top products, and spotted non-product stock codes like POST and BANK CHARGES.
- Plotted invoices by month, weekday and hour.
- Ran correlation, VIF and IQR outlier checks on Quantity and Price.

## 2. Data Pre-processing

I cleaned the data without touching the raw file, then prepared it for modelling.

- Standardized column names, text and data types.
- Removed the exact duplicates.
- Flagged cancellations, non-product rows, and invalid quantities or prices, and calculated a line total for each row.
- Excluded orders that were entered and then reversed within 24 hours.
- Ended up with about 1,003,000 clean purchases and about 17,900 real-product cancellations.
- Split the purchases by date into train, validation and test sets.
- Built a product catalog, customer-product interactions, and cancellation rates, all from the training period only.
- Created the customer lapse dataset: features from past behaviour, plus a label for whether the customer bought again in the next 90 days.
- Ran final data-quality checks and exported 13 CSV files.