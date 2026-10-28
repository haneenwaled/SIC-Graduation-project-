import pandas as pd
import pytest

from src.customer_data import CustomerData, CustomerDataError, validate_customer_frame


@pytest.fixture
def cd(data_dir) -> CustomerData:
    return CustomerData.from_csv(data_dir / "customer_lapse_predictions.csv")


def test_valid_file_loads_with_clean_report(cd):
    assert cd.report.ok and cd.report.rows_valid == 8


def test_missing_column_raises():
    with pytest.raises(CustomerDataError) as exc:
        validate_customer_frame(pd.DataFrame({"customer_id": [1], "snapshot_date": ["2011-01-01"]}))
    assert "lapse_probability" in str(exc.value) and "risk_category" in str(exc.value)


def test_missing_csv_file_reports_filename(tmp_path):
    with pytest.raises(CustomerDataError) as exc:
        CustomerData.from_csv(tmp_path / "customer_lapse_predictions.csv")
    assert "customer_lapse_predictions.csv" in str(exc.value)


def test_invalid_rows_are_excluded_and_reported():
    raw = pd.DataFrame({
        "customer_id": [1, None, 3, 4, 5, 5, 6],
        "snapshot_date": ["2011-01-01"] * 4 + ["2011-01-01", "2011-01-01", "not-a-date"],
        "lapse_probability": [0.9, 0.8, 1.5, 0.2, 0.7, 0.7, 0.4],
        "risk_category": ["High", "High", "High", "Banana", "High", "High", "Medium"],
    })
    df, rep = validate_customer_frame(raw)
    assert list(df["customer_id"]) == [1, 5]
    assert rep.invalid_rows == 4 and rep.duplicate_rows == 1 and not rep.ok


def test_category_conflicting_with_thresholds_is_excluded():
    raw = pd.DataFrame({"customer_id": [1, 2], "snapshot_date": ["2011-01-01"] * 2,
                        "lapse_probability": [0.9, 0.1], "risk_category": ["Low", "Low"]})
    df, rep = validate_customer_frame(raw)
    assert list(df["customer_id"]) == [2] and rep.tier_mismatch_rows == 1


def test_all_rows_invalid_raises(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("customer_id,snapshot_date,lapse_probability,risk_category\n1,2011-01-01,9,High\n")
    with pytest.raises(CustomerDataError):
        CustomerData.from_csv(p)


def test_latest_snapshot_and_snapshot_list(cd):
    assert cd.latest_snapshot() == pd.Timestamp("2011-09-01")
    assert cd.snapshots() == [pd.Timestamp("2011-08-01"), pd.Timestamp("2011-09-01")]


def test_counts_by_category_use_distinct_customers_and_selected_snapshot(cd):
    latest = cd.counts_by_category().set_index("risk_category")["customers"].to_dict()
    assert latest == {"Low": 1, "Medium": 2, "High": 3}
    older = cd.counts_by_category("2011-08-01").set_index("risk_category")["customers"].to_dict()
    assert older == {"Low": 1, "Medium": 0, "High": 1}
    assert cd.total_customers() == 6 and cd.total_rows() == 6
    assert cd.counts_by_category()["percent"].sum() == pytest.approx(100.0, abs=0.2)


def test_sort_by_probability_descending_with_deterministic_ties(cd):
    top = cd.sort_by_probability(n=3)
    assert list(top["customer_id"]) == [5, 1, 2]
    assert top["lapse_probability"].is_monotonic_decreasing
    low = cd.sort_by_probability(ascending=True, n=1)
    assert int(low["customer_id"].iloc[0]) == 4


def test_customer_lookup_returns_all_snapshots_newest_first(cd):
    rec = cd.get_customer(1)
    assert list(rec["snapshot_date"]) == [pd.Timestamp("2011-09-01"), pd.Timestamp("2011-08-01")]
    assert cd.get_customer(999).empty


def test_customers_in_category(cd):
    med = cd.customers_in_category("medium")
    assert set(med["customer_id"]) == {3, 6}
    assert list(med["customer_id"]) == [3, 6]  # 0.40 before 0.30


def test_urgency_percentile(cd):
    assert cd.urgency_percentile(5) == pytest.approx(83.3, abs=0.1)
    assert cd.urgency_percentile(4) == 0.0
    assert cd.urgency_percentile(12345) is None
