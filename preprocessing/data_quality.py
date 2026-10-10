import logging
from typing import Dict, Any, Optional
import pandas as pd
logger = logging.getLogger('SEMS.DataQuality')

class DataQualityReporter:

    def __init__(self):
        pass

    def generate_report(self, audit_log: Dict[str, Dict[str, Any]], processed_data: Dict[str, pd.DataFrame]) -> str:
        w_audit = audit_log.get('weather', {})
        e_audit = audit_log.get('energy', {})
        t_audit = audit_log.get('tneb', {})
        w_df = processed_data.get('weather', pd.DataFrame())
        e_df = processed_data.get('energy', pd.DataFrame())
        t_df = processed_data.get('tneb', pd.DataFrame())
        c_df = processed_data.get('combined', pd.DataFrame())

        def get_span(df: pd.DataFrame, col: str='timestamp') -> str:
            if df.empty or col not in df.columns:
                return 'N/A'
            try:
                ts = pd.to_datetime(df[col], utc=True)
                return f"{ts.min().strftime('%Y-%m-%d %H:%M')} to {ts.max().strftime('%Y-%m-%d %H:%M')} UTC"
            except Exception:
                return 'N/A'
        report_lines = ['========================================', 'DATA PREPROCESSING QUALITY REPORT', '========================================', '', 'Weather Data (OpenWeatherMap)', f"  Source          : {w_audit.get('source', 'OpenWeatherMap')}", f"  Records Before  : {w_audit.get('initial_records', len(w_df))}", f"  Duplicates      : {w_audit.get('duplicates_removed', 0)}", f"  Missing Handled : {w_audit.get('missing_before', 0)} ({w_audit.get('missing_method', 'ffill')})", f"  Invalid Filtered: {w_audit.get('invalid_removed', 0)}", f"  Final Records   : {w_audit.get('final_records', len(w_df))}", f'  Feature Count   : {w_df.shape[1]} features', f"  Time Range      : {get_span(w_df, 'timestamp')}", '', 'Smart Meter Energy Data (Household Load)', f"  Source          : {e_audit.get('source', 'Smart Meter')}", f"  Records Before  : {e_audit.get('initial_records', len(e_df))}", f"  Duplicates      : {e_audit.get('duplicates_removed', 0)}", f"  Missing Handled : {e_audit.get('missing_before', 0)} ({e_audit.get('missing_method', 'interpolate_ffill')})", f"  Invalid Filtered: {e_audit.get('invalid_removed', 0)}", f"  Final Records   : {e_audit.get('final_records', len(e_df))}", f'  Feature Count   : {e_df.shape[1]} features', f"  Time Range      : {get_span(e_df, 'timestamp')}", '', 'TNEB Historical Billing Data (Kaggle)', f"  Source          : {t_audit.get('source', 'TNEB Kaggle Historical')}", f"  Records Before  : {t_audit.get('initial_records', len(t_df))}", f"  Duplicates      : {t_audit.get('duplicates_removed', 0)}", f"  Missing Handled : {t_audit.get('missing_before', 0)}", f"  Invalid Filtered: {t_audit.get('invalid_removed', 0)}", f"  Final Records   : {t_audit.get('final_records', len(t_df))}", f'  Feature Count   : {t_df.shape[1]} features', f"  Billing Cycles  : {get_span(t_df, 'billing_date')}", '', 'Synchronized ML-Ready Dataset (15-Min Granularity)', f'  Total Records   : {len(c_df)}', f'  Feature Count   : {c_df.shape[1]} features', f"  Time Range      : {get_span(c_df, 'timestamp')}", f"  Features        : {', '.join(c_df.columns.tolist()[:8])} ...", '', '========================================', 'PREPROCESSING COMPLETE', '========================================']
        report_str = '\n'.join(report_lines)
        return report_str

    def print_summary(self, audit_log: Dict[str, Dict[str, Any]], processed_data: Dict[str, pd.DataFrame]):
        report = self.generate_report(audit_log, processed_data)
        print(report)
        return report
