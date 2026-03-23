import smtplib
import datetime
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from constant_vars import (
    indicators_data_csv,
    indicators_result_csv_path_large, indicators_result_csv_path_mid,
    indicators_result_csv_path_small, indicators_result_csv_path_full,
    sector_analysis_csv,
)
from dotenv import load_dotenv
import os

# ── Constants ─────────────────────────────────────────────────────────────────

_SIGNAL_BG = {
    'Strong Buy': '#c6efce', 'Buy': '#e2efda', 'Hold': '#f2f2f2',
    'Sell': '#fce4d6', 'Strong Sell': '#f4b8b8',
}
_SIGNAL_FG = {
    'Strong Buy': '#1a6b1a', 'Buy': '#276221', 'Hold': '#555555',
    'Sell': '#a93226', 'Strong Sell': '#7b1818',
}
_CONF_BG = ['#f4b8b8', '#fce4d6', '#fff3cd', '#e2efda', '#c6efce']

# Proper email HTML head: DOCTYPE + meta viewport + media queries only.
# All other styles must be inline so Gmail / Outlook do not strip them.
_HTML_HEAD = '''\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="format-detection" content="telephone=no,address=no,email=no">
  <title>Stock Alert</title>
  <style type="text/css">
    body,#bodyTable{{margin:0;padding:0;background-color:#f0f4f8;-webkit-text-size-adjust:100%;}}
    table{{border-collapse:collapse;mso-table-lspace:0;mso-table-rspace:0;}}
    a{{color:#005792;text-decoration:none;}}
    /* Mobile — stack metric and cap cards */
    @media screen and (max-width:599px){{
      .outer-wrap{{padding:8px 4px !important;}}
      .wrapper{{width:100% !important;}}
      .m-block{{display:block !important;width:100% !important;box-sizing:border-box !important;margin-bottom:6px !important;}}
      .m-hide{{display:none !important;max-height:0 !important;overflow:hidden !important;mso-hide:all;}}
      .stat-val{{font-size:18px !important;}}
      .stat-lbl{{font-size:10px !important;}}
      .dtable{{font-size:11px !important;}}
      .dtable td,.dtable th{{padding:5px 3px !important;}}
    }}
  </style>
</head>'''


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _e(s):
    """Escape HTML special characters."""
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _signal_badge(sig):
    bg = _SIGNAL_BG.get(sig, '#f2f2f2')
    fg = _SIGNAL_FG.get(sig, '#333')
    return (
        f'<span style="display:inline-block;background-color:{bg};color:{fg};'
        f'border:1px solid {fg};padding:2px 8px;border-radius:20px;'
        f'font-size:11px;font-weight:bold;white-space:nowrap">{_e(sig)}</span>'
    )


def _section_header(title, bg='#005792'):
    """Coloured section title bar that sits flush on top of the table below it."""
    return (
        f'<table border="0" cellpadding="0" cellspacing="0" width="600"'
        f' style="margin-top:22px">'
        f'<tr><td bgcolor="{bg}" style="background-color:{bg};padding:11px 14px;'
        f'border-radius:6px 6px 0 0">'
        f'<span style="color:white;font-size:14px;font-weight:bold">{title}</span>'
        f'</td></tr></table>'
    )


def _preheader(text):
    """Hidden preview text that appears as the inbox snippet below the subject line.
    Padded with zero-width non-joiners so email body content doesn't leak through."""
    safe    = _e(str(text)[:120])
    padding = '&nbsp;&zwnj;' * 60
    return (
        '<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;'
        'font-size:1px;line-height:1px;color:#f0f4f8">'
        f'{safe}{padding}</div>'
    )


def _metric_card(value, label, bg, fg='#ffffff', value_size='22px', width=192):
    """One stat card; renders as a <td> with explicit width for reliable table layout."""
    return (
        f'<td class="m-block" bgcolor="{bg}" width="{width}"'
        f' style="background-color:{bg};width:{width}px;padding:16px 10px;border-radius:8px;'
        f'text-align:center;vertical-align:middle">'
        f'<div class="stat-val" style="font-size:{value_size};font-weight:700;color:{fg};line-height:1.1">{_e(str(value))}</div>'
        f'<div class="stat-lbl" style="font-size:11px;color:{fg};opacity:0.85;margin-top:5px">{label}</div>'
        f'</td>'
    )


def _cap_scorecard(label, icon, buys, holds, sells, avg_score, width=192):
    """One cap scorecard; renders as a <td> with explicit pixel width."""
    bar_pct = min(max(int((avg_score + 1) / 2 * 100), 0), 100)
    colour  = '#1a7a1a' if avg_score >= 0.2 else ('#a93226' if avg_score <= -0.1 else '#555')
    sign    = '+' if avg_score >= 0 else ''
    return (
        f'<td class="m-block" bgcolor="#ffffff" valign="top" width="{width}"'
        f' style="background-color:#ffffff;border:1px solid #dde3ea;border-radius:8px;'
        f'padding:14px;vertical-align:top;width:{width}px">'
        f'<div style="font-size:13px;font-weight:bold;color:#005792;margin-bottom:9px">{icon} {_e(label)}</div>'
        f'<table border="0" cellpadding="3" cellspacing="0" width="100%" style="border-collapse:collapse">'
        f'<tr><td style="color:#276221;font-size:12px">✅ Buy</td>'
        f'    <td align="right" style="font-weight:bold;color:#276221;font-size:12px">{buys}</td></tr>'
        f'<tr><td style="color:#555;font-size:12px">⏸ Hold</td>'
        f'    <td align="right" style="font-weight:bold;font-size:12px">{holds}</td></tr>'
        f'<tr><td style="color:#a93226;font-size:12px">🔻 Sell</td>'
        f'    <td align="right" style="font-weight:bold;color:#a93226;font-size:12px">{sells}</td></tr>'
        f'</table>'
        f'<div style="margin-top:9px;font-size:11px;color:#555">Avg Score: '
        f'<b style="color:{colour}">{sign}{avg_score:.3f}</b></div>'
        f'<div bgcolor="#dde3ea" style="background-color:#dde3ea;border-radius:4px;height:5px;margin-top:4px">'
        f'<div style="background-color:{colour};width:{bar_pct}%;height:5px;border-radius:4px"></div></div>'
        f'</td>'
    )


def _stock_table(df, cols_to_show=None):
    """
    Mobile-safe email table. Fixed 600 px. Shows curated columns;
    AI summary appears as a muted sub-row beneath each stock row.
    """
    # Column: (header label, fixed px width, visible on mobile)
    _COL_META = {
        'symbol':               ('Symbol', 88,  True),
        'close_price':          ('Price',  65,  True),
        'signal':               ('Signal', 92,  True),
        'confidence':           ('Conf',   48,  True),
        'composite_score':      ('Score',  55,  True),
        'rsi_signal':           ('RSI',    48,  False),
        'bollinger_signal':     ('Boll',   48,  False),
        'supertrend_direction': ('ST Dir', 56,  False),
        'volume_signal':        ('Volume', 100, False),
        'category':             ('Cap',    50,  False),
        'sector':               ('Sector', 90,  False),
        'perc_high':            ('%Hi',    48,  False),
        'perc_low':             ('%Lo',    48,  False),
    }
    priority = ['symbol', 'close_price', 'signal', 'confidence', 'composite_score',
                'rsi_signal', 'bollinger_signal', 'supertrend_direction', 'volume_signal']
    if cols_to_show is None:
        cols_to_show = [c for c in priority if c in df.columns]

    has_summary = 'ai_summary' in df.columns

    # Header
    th_cells = ''
    for col in cols_to_show:
        lbl, w, mobile = _COL_META.get(col, (col, 70, False))
        hide = '' if mobile else ' class="m-hide"'
        th_cells += (
            f'<th{hide} width="{w}"'
            f' style="padding:8px 8px;background-color:#005792;color:white;'
            f'font-size:12px;font-weight:600;white-space:nowrap;text-align:left">{_e(lbl)}</th>'
        )

    # Data rows
    rows_html = []
    for _, row in df.iterrows():
        sig    = str(row.get('signal', ''))
        row_bg = _SIGNAL_BG.get(sig, '#ffffff')

        cells = ''
        for col in cols_to_show:
            _, w, mobile = _COL_META.get(col, ('', 70, False))
            hide   = '' if mobile else ' class="m-hide"'
            val    = row.get(col, '')
            td_pad = 'padding:7px 8px'

            if col == 'symbol':
                s = _e(str(val))
                link = (
                    f'<a href="https://www.nseindia.com/get-quotes/equity?symbol={s}"'
                    f' style="color:#005792;font-weight:bold" target="_blank">{s}</a>'
                )
                cells += f'<td{hide} bgcolor="{row_bg}" style="background-color:{row_bg};{td_pad}">{link}</td>'

            elif col == 'signal':
                cells += f'<td{hide} bgcolor="{row_bg}" style="background-color:{row_bg};{td_pad}">{_signal_badge(sig)}</td>'

            elif col == 'confidence':
                try:
                    ci = min(int(float(val)), 4)
                except Exception:
                    ci = 0
                cbg = _CONF_BG[ci]
                cells += (
                    f'<td{hide} bgcolor="{cbg}" align="center"'
                    f' style="background-color:{cbg};{td_pad};font-weight:bold;font-size:12px;text-align:center">{ci}/4</td>'
                )

            elif col == 'close_price':
                try:
                    pv = f'₹{float(val):,.2f}'
                except Exception:
                    pv = _e(str(val))
                cells += f'<td{hide} bgcolor="{row_bg}" style="background-color:{row_bg};{td_pad}">{pv}</td>'

            elif col == 'composite_score':
                try:
                    sv = f'{float(val):+.3f}'
                except Exception:
                    sv = _e(str(val))
                cells += (
                    f'<td{hide} bgcolor="{row_bg}" align="center"'
                    f' style="background-color:{row_bg};{td_pad};text-align:center;font-weight:bold">{sv}</td>'
                )

            elif col in ('rsi_signal', 'bollinger_signal'):
                sbg = '#e2efda' if str(val) == 'buy' else ('#fce4d6' if str(val) == 'sell' else '#f2f2f2')
                cells += (
                    f'<td{hide} bgcolor="{sbg}" align="center"'
                    f' style="background-color:{sbg};{td_pad};text-align:center;font-size:11px">{_e(str(val))}</td>'
                )

            elif col == 'supertrend_direction':
                sbg = '#e2efda' if str(val) == 'bullish' else ('#fce4d6' if str(val) == 'bearish' else '#f2f2f2')
                cells += (
                    f'<td{hide} bgcolor="{sbg}" align="center"'
                    f' style="background-color:{sbg};{td_pad};text-align:center;font-size:11px">{_e(str(val))}</td>'
                )

            else:
                cells += f'<td{hide} bgcolor="{row_bg}" style="background-color:{row_bg};{td_pad};font-size:12px">{_e(str(val))}</td>'

        rows_html.append(f'<tr>{cells}</tr>')

        # AI summary sub-row — shown on all screens, italic muted line below each stock
        if has_summary:
            raw   = str(row.get('ai_summary', ''))
            snip  = (raw[:135] + '…') if len(raw) > 135 else raw
            ncols = len(cols_to_show)
            rows_html.append(
                f'<tr bgcolor="#f7f9fc"><td colspan="{ncols}"'
                f' style="background-color:#f7f9fc;padding:3px 10px 8px 10px;'
                f'font-size:11px;color:#777;font-style:italic;'
                f'border-bottom:1px solid #e0e6ee">{_e(snip)}</td></tr>'
            )

    return (
        f'<table class="dtable" border="0" cellpadding="0" cellspacing="0" width="600"'
        f' style="width:600px;max-width:600px;table-layout:fixed;font-size:13px;'
        f'border:1px solid #dde3ea;border-top:none">'
        f'<thead><tr>{th_cells}</tr></thead>'
        f'<tbody>{chr(10).join(rows_html)}</tbody>'
        f'</table>'
    )


def _sector_table(df_sec):
    """Compact sector summary table."""
    clean_cols = [c for c in df_sec.columns if not c.startswith('Unnamed')]
    th = ''.join(
        f'<th style="padding:8px 10px;background-color:#6c3483;color:white;'
        f'font-size:12px;white-space:nowrap;text-align:left">{_e(c)}</th>'
        for c in clean_cols
    )
    rows = []
    for i, (_, row) in enumerate(df_sec.iterrows()):
        row_bg = '#ffffff' if i % 2 == 0 else '#f7f0fa'
        cells  = ''
        for col in clean_cols:
            val = row.get(col, '')
            try:
                fval    = float(val)
                display = f'{fval:.3f}' if '.' in str(val) else str(int(fval))
            except (ValueError, TypeError):
                display = _e(str(val))
            cells += (
                f'<td bgcolor="{row_bg}"'
                f' style="background-color:{row_bg};padding:7px 10px;font-size:13px">{display}</td>'
            )
        rows.append(f'<tr>{cells}</tr>')
    return (
        f'<table border="0" cellpadding="0" cellspacing="0" width="600"'
        f' style="width:600px;max-width:600px;font-size:13px;border:1px solid #dde3ea;border-top:none">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _top_picks_block(df_v):
    """Top 10 buy signals by composite score."""
    if 'signal' not in df_v.columns:
        return ''
    df_picks = (
        df_v[df_v['signal'].isin(['Buy', 'Strong Buy'])]
        .sort_values('composite_score', ascending=False)
        .head(10)
    )
    if df_picks.empty:
        return ''
    pick_cols = [c for c in ['symbol', 'category', 'close_price', 'signal', 'confidence', 'composite_score']
                 if c in df_picks.columns]
    return _section_header('🏆 Top Picks — Highest Conviction Buy Signals', '#276221') + _stock_table(df_picks, pick_cols)


def _dashboard_block(df_all, df_sec=None):
    """Dashboard card: metric stat row + cap scorecards + top picks."""
    df = df_all.copy()
    for col, fill in (('close_price', float('nan')), ('composite_score', 0.0), ('confidence', 0.0)):
        df[col] = pd.to_numeric(df.get(col, pd.Series(dtype=float)), errors='coerce').fillna(fill)
    df_v = df[df['close_price'].notna()]

    vc          = df_v['signal'].value_counts() if 'signal' in df_v.columns else pd.Series(dtype=int)
    total       = len(df)
    total_buys  = int(vc.get('Buy', 0) + vc.get('Strong Buy', 0))
    total_sells = int(vc.get('Sell', 0) + vc.get('Strong Sell', 0))
    strong_sigs = int((df_v['confidence'] == 4).sum())

    top_sector = '\u2014'
    if df_sec is not None and not df_sec.empty and 'sector' in df_sec.columns:
        try:
            sc = 'buy_signals' if 'buy_signals' in df_sec.columns else df_sec.columns[1]
            top_sector = str(df_sec.sort_values(sc, ascending=False).iloc[0]['sector'])[:20]
        except Exception:
            pass

    # ── Metric cards: 3 cols × 192 px + cellspacing=6 → 600 px ──────────
    # cellspacing="6" is a reliable HTML attribute (not CSS) supported by all clients.
    # (3+1)*6 + 3*192 = 24 + 576 = 600 px exact.
    r1 = (
        '<tr>'
        + _metric_card(total,       '\U0001f4cb Scanned',      '#2c3e50', width=192)
        + _metric_card(total_buys,  '\u2705 Buy Signals',   '#1a7a1a', width=192)
        + _metric_card(total_sells, '\U0001f53b Sell Signals', '#a93226', width=192)
        + '</tr>'
    )
    r2 = (
        '<tr>'
        + _metric_card(strong_sigs, '\u26a1 All-4 Aligned',   '#6c3483', width=192)
        + _metric_card(top_sector,  '\U0001f3c6 Top Sector',   '#005792', value_size='13px', width=192)
        + '<td width="192" bgcolor="#eef2f7" style="background-color:#eef2f7;border-radius:8px;width:192px"></td>'
        + '</tr>'
    )
    metrics_html = (
        '<table border="0" cellpadding="0" cellspacing="6" width="600">'
        + r1 + r2 + '</table>'
    )

    # ── Cap scorecards: 3 cols × 192 px + cellspacing=6 → 600 px ──────────
    cap_cells = ''
    for cat, icon, label in [('large', '\U0001f3e6', 'Large Cap'), ('mid', '\U0001f4ca', 'Mid Cap'), ('small', '\U0001f4c8', 'Small Cap')]:
        sub = df_v[df_v['category'] == cat] if 'category' in df_v.columns else pd.DataFrame()
        if sub.empty:
            cap_cells += (
                f'<td class="m-block" bgcolor="#f7f7f7" valign="top" width="192"'
                f' style="background-color:#f7f7f7;border-radius:8px;padding:14px;'
                f'color:#aaa;text-align:center;font-size:13px;width:192px">'
                f'{icon} {_e(label)}<br><span style="font-size:11px">No data</span></td>'
            )
        else:
            vc2   = sub['signal'].value_counts()
            buys  = int(vc2.get('Buy', 0) + vc2.get('Strong Buy', 0))
            holds = int(vc2.get('Hold', 0))
            sells = int(vc2.get('Sell', 0) + vc2.get('Strong Sell', 0))
            avg   = float(sub['composite_score'].mean())
            cap_cells += _cap_scorecard(label, icon, buys, holds, sells, avg, width=192)

    cap_html = (
        '<table border="0" cellpadding="0" cellspacing="6" width="600"'
        ' style="margin-top:4px">'
        f'<tr>{cap_cells}</tr></table>'
    )

    # Snapshot card: section-header forms the coloured top bar; white content card below.
    # TD padding is 0 horizontal so 600 px inner tables don't overflow the card.
    snapshot = (
        _section_header('\U0001f4ca Today\'s Market Snapshot', '#1a3a5c')
        + '<table border="0" cellpadding="0" cellspacing="0" width="600" bgcolor="#ffffff"'
        ' style="background-color:#ffffff;border:1px solid #dde3ea;border-top:none;'
        'border-radius:0 0 8px 8px;margin-bottom:6px">'
        '<tr><td style="padding:14px 0 12px 0">'
        + metrics_html + cap_html
        + '</td></tr></table>'
    )
    return snapshot + _top_picks_block(df_v)


def _build_html(header_inner, body_parts, footer_text='', preheader=''):
    """
    Assemble a complete, mobile-safe HTML email document.
    All layout is table-based with width="600" and bgcolor attributes
    so iOS Mail, Gmail App (Android) and Outlook all render correctly.
    """
    body_joined = ''.join(body_parts)
    footer = footer_text or 'Automated stock alert &middot; Generated by your analytics bot 🤖'
    pre = _preheader(preheader) if preheader else ''
    return (
        _HTML_HEAD
        + '<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:Arial,Helvetica,sans-serif">'
        + pre
        # Outer container — full-width background
        + '<table id="bodyTable" border="0" cellpadding="0" cellspacing="0" width="100%"'
        ' bgcolor="#f0f4f8" style="background-color:#f0f4f8">'
        '<tr><td class="outer-wrap" align="center" style="padding:20px 10px">'

        # 600 px wrapper
        '<table class="wrapper" border="0" cellpadding="0" cellspacing="0" width="600" align="center">'

        # Header band
        '<tr><td bgcolor="#005792" style="background-color:#005792;'
        'border-radius:8px 8px 0 0;padding:22px 22px 18px 22px">'
        + header_inner +
        '</td></tr>'

        # Body — zero horizontal padding so all 600 px tables sit flush without overflow
        '<tr><td bgcolor="#f7f9fc" style="background-color:#f7f9fc;padding:12px 0 0 0">'
        + body_joined +
        '</td></tr>'

        # Footer
        '<tr><td bgcolor="#e8edf2" style="background-color:#e8edf2;'
        'padding:14px 18px;border-radius:0 0 8px 8px;border-top:1px solid #d0d8e4;text-align:center">'
        f'<p style="font-size:11px;color:#888;margin:0">{footer}</p>'
        '</td></tr>'

        '</table>'  # close wrapper
        '</td></tr></table>'  # close outer
        '</body></html>'
    )


def _send_email(smtp_conn, sender, recipients, subject, html_body, attachments=None):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = sender
    msg['To']      = ', '.join(recipients) if isinstance(recipients, list) else recipients
    # UTF-8 charset so ₹ and emoji render correctly on all clients
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    if attachments:
        for path in attachments:
            try:
                with open(path, 'rb') as f:
                    msg.attach(MIMEApplication(f.read(), Name=os.path.basename(path)))
            except Exception:
                pass
    smtp_conn.sendmail(sender, recipients, msg.as_string())


def mail_message():
    try:
        load_dotenv()
        EMAIL_ID_LIST = eval(os.getenv('EMAIL_ID_LIST'))  # noqa: S307 — TODO: replace with json.loads
        SENDER_EMAIL = os.getenv('SENDER_EMAIL')
        SENDER_EMAIL_PASSWORD = os.getenv('SENDER_EMAIL_PASSWORD')

        now_str    = datetime.datetime.now().strftime('%B %d, %Y')
        ts_str     = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        date_short = datetime.datetime.now().strftime('%b %d')

        # Load full dataset once — used for summary stats and strong signal check
        df_all = pd.DataFrame()
        try:
            df_all = pd.read_csv(indicators_data_csv)
            df_all['close_price'] = pd.to_numeric(df_all['close_price'], errors='coerce')
        except Exception:
            pass

        # Pre-compute summary stats for subjects and preheader
        _total      = len(df_all)
        _vc         = df_all['signal'].value_counts() if 'signal' in df_all.columns else pd.Series(dtype=int)
        _buys       = int(_vc.get('Buy', 0) + _vc.get('Strong Buy', 0))
        _sells      = int(_vc.get('Sell', 0) + _vc.get('Strong Sell', 0))
        _strong     = int((pd.to_numeric(df_all.get('confidence', pd.Series(dtype=float)), errors='coerce') == 4).sum()) if not df_all.empty else 0
        _holds      = int(_vc.get('Hold', 0))

        email_body_parts    = []
        attachments_to_send = []

        # Load sector data early — used in dashboard top-sector card
        df_sec = pd.DataFrame()
        try:
            df_sec = pd.read_csv(sector_analysis_csv)
        except Exception:
            pass

        # ── Dashboard (snapshot + top picks) ──────────────────────────────
        if not df_all.empty:
            email_body_parts.append(_dashboard_block(df_all, df_sec if not df_sec.empty else None))

        # ── Sector hotspots ───────────────────────────────────────────────
        if not df_sec.empty:
            email_body_parts.append(
                _section_header('🏭 Sector Hotspots (≥2 Buy Signals)', '#6c3483')
                + _sector_table(df_sec)
                + '<div style="height:8px"></div>'
            )

        # ── Per-cap detail tables ─────────────────────────────────────────
        def _attach_cap(df_path, label, icon, hdr_bg):
            try:
                df = pd.read_csv(df_path)
                df['close_price'] = pd.to_numeric(df.get('close_price', pd.Series(dtype=float)), errors='coerce')
                df = df[df['close_price'].notna()]
                df.dropna(axis=1, how='all', inplace=True)
                if not df.empty:
                    email_body_parts.append(
                        _section_header(f'{icon} {label}', hdr_bg)
                        + _stock_table(df)
                        + '<div style="height:8px"></div>'
                    )
                    attachments_to_send.append(df_path)
                else:
                    print(f'Skipping {label}: no data after filtering.')
            except Exception as e:
                print(f'Error processing {label}: {e}')

        _attach_cap(indicators_result_csv_path_large, 'Large Cap', '🏦', '#1a3a5c')
        _attach_cap(indicators_result_csv_path_mid,   'Mid Cap',   '📊', '#1a5c4a')
        _attach_cap(indicators_result_csv_path_small, 'Small Cap', '📈', '#2c5c1a')

        # Full CSV attachment only (no inline rendering — too wide)
        try:
            df_full = pd.read_csv(indicators_result_csv_path_full)
            df_full['close_price'] = pd.to_numeric(df_full['close_price'], errors='coerce')
            if not df_full[df_full['close_price'].notna()].empty:
                if indicators_result_csv_path_full not in attachments_to_send:
                    attachments_to_send.append(indicators_result_csv_path_full)
        except Exception as e:
            print(f'Full report attachment error: {e}')

        if not email_body_parts:
            print('⚠️ No data to send. Email skipped.')
            return

        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(SENDER_EMAIL, SENDER_EMAIL_PASSWORD)

        # ── Main daily alert ──────────────────────────────────────────────
        strong_prefix = '🚨 ' if _strong > 0 else ''
        main_subject  = (
            f'{strong_prefix}📈 {_buys} Buys · {_sells} Sells'
            + (f' · {_strong}⚡ Strong' if _strong > 0 else '')
            + f' · {date_short}'
        )
        main_preheader = (
            f'{_total} stocks scanned · {_buys} buys · {_sells} sells · {_holds} holds'
            + (f' · {_strong} all-4-aligned signal{"s" if _strong > 1 else ""}' if _strong > 0 else '')
        )
        header_inner = (
            f'<h1 style="margin:0 0 5px 0;font-size:24px;font-weight:700;color:#ffffff">📈 Daily Stock Alert</h1>'
            f'<p style="margin:0;font-size:13px;color:rgba(255,255,255,0.82)">{now_str}</p>'
        )
        main_html = _build_html(header_inner, email_body_parts, preheader=main_preheader)
        _send_email(s, SENDER_EMAIL, EMAIL_ID_LIST, main_subject, main_html, attachments_to_send)
        print('✅ Main alert email sent.')

        # ── Strong signal alert (all 4 indicators aligned) ────────────────
        if not df_all.empty and 'confidence' in df_all.columns:
            try:
                df_strong = df_all[
                    (pd.to_numeric(df_all['confidence'], errors='coerce') == 4)
                    & df_all['close_price'].notna()
                ].copy()
                if not df_strong.empty:
                    n = len(df_strong)
                    strong_subject  = f'🚨 {n} Strong Signal{"s" if n>1 else ""} · All 4 Indicators Aligned · {date_short}'
                    strong_preheader = ', '.join(str(s) for s in df_strong['symbol'].tolist()[:8]) + (' …' if n > 8 else '')
                    strong_header = (
                        f'<h1 style="margin:0 0 5px 0;font-size:22px;font-weight:700;color:#ffffff">🚨 Strong Signal Alert</h1>'
                        f'<p style="margin:0;font-size:13px;color:rgba(255,255,255,0.82)">{n} stock{"s" if n>1 else ""} with all 4 indicators aligned · {now_str}</p>'
                    )
                    strong_body = [
                        '<table border="0" cellpadding="0" cellspacing="0" width="600"'
                        ' style="margin-bottom:14px"><tr>'
                        '<td bgcolor="#fff3cd" style="background-color:#fff3cd;border-left:4px solid #e6960c;'
                        'padding:11px 14px;border-radius:4px;font-size:13px;color:#5a3e00">'
                        '<b>Highest conviction signals — all 4 indicators agree on direction.</b>'
                        '</td></tr></table>',
                        _stock_table(df_strong),
                    ]
                    strong_html = _build_html(strong_header, strong_body, preheader=strong_preheader)
                    _send_email(s, SENDER_EMAIL, EMAIL_ID_LIST, strong_subject, strong_html)
                    print(f'✅ Strong signal alert sent ({n} stocks).')
                else:
                    print('ℹ️ No all-4-aligned stocks — strong signal email skipped.')
            except Exception as e:
                print(f'Strong signal alert skipped: {e}')

        s.quit()

    except smtplib.SMTPException as e:
        print(f'SMTP Error: {e}')
    except Exception as e:
        print(f'Unexpected error: {e}')
