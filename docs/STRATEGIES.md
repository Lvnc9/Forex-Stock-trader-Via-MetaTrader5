# TradeBot — Strategies user guide

How to use the **Strategies** section: create, edit, and manage trading strategies for backtest and live MT5.

Login URL: `/login/` · Strategies URL: `/strategies/`

Prerequisites (once):

```bash
cd tradeBot && source venv/bin/activate
python manage.py migrate
python manage.py seed_library_strategies
python manage.py seed_rule_templates
python manage.py runserver
```

---

## 1. Overview

TradeBot strategies are **Python logic** (not MQL). The same strategy runs in backtest and on the Windows MT5 agent.

There are **three kinds** of strategies:

| Type | Badge on list | What it is | Best for |
|------|---------------|------------|----------|
| **Library** | Library | Built-in Python strategies | Fast start with MA / RSI / breakout |
| **Rules** | Rules | Visual rule builder → JSON `rule_spec` | No-code / low-code setups |
| **Custom Python** | Python | Your own `BaseStrategy` class | Full control, complex logic |

All saved instances appear under **Saved strategies**. From there you edit parameters, duplicate, delete, then **backtest** or **deploy**.

---

## 2. Strategies home (`/strategies/`)

The page has four areas:

1. **Actions** — *New rule strategy* · *Upload custom strategy*
2. **Library (Python)** — cards for built-in strategies → *Configure parameters*
3. **Rule templates** — starter rule-specs → *Customize rules*
4. **Saved strategies** — your configured instances (edit / duplicate / delete)

---

## 3. Library strategies (Python)

### Built-in strategies

| Name | Idea | Main parameters |
|------|------|-----------------|
| **MA crossover** | Long when fast SMA crosses above slow; short on cross below | `fast_period`, `slow_period` |
| **RSI reversal** | Long when RSI leaves oversold upward; short when leaving overbought | `rsi_period`, `oversold`, `overbought` |
| **Range breakout** | Long above prior range high; short below range low | `lookback`, `buffer_pct` |

### Steps

1. Open `/strategies/`.
2. Under **Library (Python)**, click **Configure parameters →** on a card.
3. That creates (or opens) a saved strategy row and takes you to the **Parameters** form.
4. Adjust numbers → **Save parameters**.
5. Optionally click **Run backtest →**.

Library strategies use typed parameter forms (min/max enforced). Logic stays in Python under `apps/strategies/library/`.

---

## 4. Rule templates & rule builder

Rule strategies describe **indicators + compare rules + optional SL/TP** without writing Python. They still run through the same signal engine as library strategies.

### 4.1 Templates

| Template | Purpose |
|----------|---------|
| **MA cross (rules)** | Fast SMA crosses slow SMA |
| **RSI reversal (rules)** | RSI crosses oversold / overbought |
| **Range breakout (rules)** | Break of lookback high/low with optional % buffer |
| **MA cross + HTF filter** | MA cross plus a higher-timeframe SMA filter |

### Steps

1. Click **Customize rules →** on a template, **or** **New rule strategy** for a blank builder.
2. Fill the builder (below) → **Create / Save rule strategy**.
3. On save, TradeBot **dry-runs** the spec on synthetic bars; invalid specs show an error and are not saved.

### 4.2 Builder sections

#### Name & description

Human labels for the saved strategy list.

#### Parameters

Tunable knobs (periods, levels, buffers).

- Starts with **1 empty row**.
- **+ Add parameter** adds another row.
- **−** removes a row.
- Fields: Name · Type (`int` / `float`) · Default · Min · Max.
- Ceiling: **24** parameters (UI only; runtime schema is open-ended).

Use parameter **names** later in indicator period params and in rule refs (`param`).

#### Indicators

Computed series used in rules.

| Field | Meaning |
|-------|---------|
| **Id** | Short id referenced in rules (e.g. `fast`, `rsi`) |
| **Fn** | `sma`, `ema`, `rsi`, `atr`, `macd`, `bollinger` |
| **Source** | `primary` = strategy timeframe · `htf` = higher timeframe |
| **Period** | Fixed period number |
| **Period param** | Or bind period to a parameter name (preferred for tuning) |
| **Column** | OHLC field (`close` default; use `high`/`low` for range highs/lows) |

- Starts with **1 row**; **+ Add indicator** / **−**.
- Ceiling: **16** indicators.

If any indicator uses **HTF**, backtest and deploy forms **require** an HTF timeframe.

#### Entry / exit rule groups

Four groups: **Entry long** · **Entry short** · **Exit long** · **Exit short**.

Each group has:

- **Logic**: `AND` or `OR` across that group’s rules.
- Rules: each rule is **Left** *op* **Right**.
- **+ Add rule** / **−** per group (ceiling **12** rules per group).

**Compare ops:** `>`, `>=`, `<`, `<=`, `==`, `cross_above`, `cross_below`.

**Left / Right refs:**

| Ref | Use |
|-----|-----|
| **indicator** | Indicator id |
| **price** | open / high / low / close |
| **value** | Literal number |
| **param** | Parameter name |
| **pct_offset** | Base ± percent (one nesting level) |
| **arith** | `+ − * /` of two simple refs (one nesting level) |

**Evaluation order (each bar):** exit rules first → then entry long → then entry short.

#### Stop loss & take profit

| Stop loss | Take profit |
|-----------|-------------|
| None | None |
| **Percent** of entry | **Percent** of entry |
| **ATR** (mult × ATR period) | **R:R** (reward multiple of stop distance) |

These attach SL/TP metadata on entry signals for backtest and live.

### 4.3 Editing a rule strategy

On **Saved strategies**, badge **Rules** → **Edit** opens the same builder with current rows filled. Save again to re-validate.

---

## 5. Custom Python strategies

### Steps

1. **Upload custom strategy** (`/strategies/custom/new/`).
2. Enter **Name**, optional **Description**, and paste **source code**.
3. Click **Validate & save**.

### Requirements

- Subclass `BaseStrategy`.
- Implement `on_bar(self, ctx) -> Signal | None`.
- Prefer setting `module_path`, `slug`, `name`, `default_parameters`, `parameter_schema`.
- Source is imported and **dry-run** on sample bars before save.
- Files live under `apps/strategies/user/`.

### Editing

Saved list badge **Python** → **Edit** updates source in place (re-validated).

### Minimal sketch

```python
from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.signals import Signal, SignalAction

class MyStrategy(BaseStrategy):
    slug = "my_strategy"
    name = "My strategy"
    module_path = "apps.strategies.user.will_be_set_on_install"
    default_parameters = {"period": 14}
    parameter_schema = [
        {"name": "period", "type": "int", "min": 2, "max": 100, "default": 14},
    ]

    def on_bar(self, ctx: BarContext) -> Signal | None:
        # return Signal(SignalAction.ENTER_LONG) / ENTER_SHORT / EXIT / None
        return None
```

After save, open **Edit** (parameters) if a parameter form is generated from `parameter_schema`, or manage knobs via the saved strategy parameters flow used for library strategies when applicable.

---

## 6. Saved strategies — manage

| Action | Behavior |
|--------|----------|
| **Edit** | Rules → rule builder · Python → source editor · Library → parameters form |
| **Duplicate** | Copy with a new name/slug; opens editor for the clone |
| **Delete** | Confirm page. **Blocked** if any backtest runs or deployments still reference the strategy |

---

## 7. After saving — backtest & deploy

### Backtest

1. Go to **Backtest** → New backtest.
2. Pick your strategy, catalog symbol, primary timeframe, date range.
3. If the strategy uses **HTF** indicators, choose a **higher** HTF timeframe (required).
4. Run and review win rate, equity, trades.

### Deploy (live / demo MT5)

1. Windows agent online with a valid token.
2. **Trading** → New deployment → choose strategy, agent, symbol map, timeframe, lot size.
3. Review screen shows parameters and last matching backtest if any.
4. **Arm deployment** — agent pulls the strategy and runs it on each new bar.

Same `on_bar` / rule engine path as backtest.

---

## 8. Limits & tips

| Topic | Detail |
|-------|--------|
| Parameter count (builder UI) | Up to 24 via **+**; start from 1 |
| Indicators / rules UI | Up to 16 indicators; 12 rules per group |
| Nested exprs | One level of `pct_offset` / `arith` only |
| HTF | Any `source=htf` indicator forces HTF on backtest/deploy |
| Delete | Remove or keep backtests/deployments first |
| Library vs rules | Same ideas; library = Python; rules = editable JSON builder |
| Seed commands | Re-run seed commands after pull to refresh library rows / templates |

---

## 9. Quick recipes

**Fast MA cross (no code)**  
Rule templates → *MA cross (rules)* → tweak periods → Save → Backtest M5 (optional HTF H1 with *MA cross + HTF filter*).

**Tune library RSI**  
Library → *RSI reversal* → Configure → change oversold/overbought → Save → Backtest.

**Custom idea**  
Upload Python subclassing `BaseStrategy` → Validate & save → Backtest → Deploy when ready.

---

# راهنمای بخش استراتژی‌ها — TradeBot

چطور از بخش **استراتژی‌ها** استفاده کنید: ساخت، ویرایش و مدیریت استراتژی برای بک‌تست و اجرای زنده روی MetaTrader 5.

آدرس ورود: `/login/` · آدرس استراتژی‌ها: `/strategies/`

یک‌بار در ابتدا:

```bash
cd tradeBot && source venv/bin/activate
python manage.py migrate
python manage.py seed_library_strategies
python manage.py seed_rule_templates
python manage.py runserver
```

---

## ۱. تصویر کلی

استراتژی‌های TradeBot با **پایتون** نوشته می‌شوند (نه MQL). همان منطق هم در بک‌تست و هم روی ایجنت ویندوز کنار MT5 اجرا می‌شود.

سه نوع استراتژی دارید:

| نوع | برچسب در لیست | یعنی چه؟ | مناسب برای |
|-----|----------------|----------|------------|
| **کتابخانه** | Library | استراتژی‌های آمادهٔ پایتونی | شروع سریع با میانگین / RSI / شکست رنج |
| **قواعد** | Rules | سازندهٔ بصری قواعد → JSON | بدون کدنویسی یا با کدنویسی کم |
| **پایتون سفارشی** | Python | کلاس `BaseStrategy` خودتان | منطق پیچیده و کنترل کامل |

نمونه‌های ذخیره‌شده در **Saved strategies** می‌آیند؛ بعد پارامتر می‌زنید، کپی می‌گیرید، حذف می‌کنید، سپس بک‌تست یا دیپلوی.

---

## ۲. صفحهٔ اصلی استراتژی‌ها (`/strategies/`)

چهار بخش:

1. **اقدامات** — *New rule strategy* · *Upload custom strategy*
2. **Library (Python)** — کارت‌های آماده → *Configure parameters*
3. **Rule templates** — قالب‌های قاعده‌محور → *Customize rules*
4. **Saved strategies** — نمونه‌های شما (ویرایش / کپی / حذف)

---

## ۳. استراتژی‌های کتابخانه (پایتون)

### استراتژی‌های آماده

| نام | ایده | پارامترهای اصلی |
|-----|------|------------------|
| **MA crossover** | ورود خرید با عبور میانگین سریع از بالای کند؛ فروش با عبور به پایین | `fast_period`, `slow_period` |
| **RSI reversal** | خرید وقتی RSI از اشباع فروش بالا می‌آید؛ فروش وقتی از اشباع خرید پایین می‌آید | `rsi_period`, `oversold`, `overbought` |
| **Range breakout** | خرید بالای سقف رنج قبلی؛ فروش زیر کف رنج | `lookback`, `buffer_pct` |

### مراحل

1. بروید به `/strategies/`.
2. زیر **Library (Python)** روی **Configure parameters →** بزنید.
3. یک ردیف ذخیره‌شده ساخته (یا باز) می‌شود و فرم **Parameters** می‌آید.
4. اعداد را تنظیم کنید → **Save parameters**.
5. در صورت تمایل **Run backtest →**.

فرم پارامترها نوع‌دار است (حداقل/حداکثر اعمال می‌شود). منطق داخل `apps/strategies/library/` می‌ماند.

---

## ۴. قالب‌های قاعده و Rule Builder

استراتژی‌های قاعده‌محور **اندیکاتور + شروط مقایسه + در صورت تمایل حد ضرر/سود** را بدون پایتون تعریف می‌کنند؛ ولی همان موتور سیگنال کتابخانه را اجرا می‌کنند.

### ۴.۱ قالب‌ها

| قالب | کاربرد |
|------|--------|
| **MA cross (rules)** | تقاطع میانگین متحرک سریع و کند |
| **RSI reversal (rules)** | عبور RSI از سطوح اشباع |
| **Range breakout (rules)** | شکست سقف/کف lookback با بافر درصدی اختیاری |
| **MA cross + HTF filter** | تقاطع MA به‌همراه فیلتر میانگین تایم‌فریم بالاتر |

### مراحل

1. روی قالب **Customize rules →** بزنید، یا با **New rule strategy** از صفر شروع کنید.
2. فرم سازنده را پر کنید → **Create / Save rule strategy**.
3. هنگام ذخیره، سیستم روی دادهٔ مصنوعی **dry-run** می‌کند؛ اگر خطا باشد ذخیره نمی‌شود.

### ۴.۲ بخش‌های سازنده

#### نام و توضیح

برای نمایش در لیست ذخیره‌شده‌ها.

#### پارامترها (Parameters)

دکمه‌های قابل تنظیم (دوره، سطح، بافر).

- با **۱ ردیف خالی** شروع می‌شود.
- **+ Add parameter** ردیف جدید می‌آورد.
- **−** ردیف را برمی‌دارد.
- فیلدها: نام · نوع (`int` / `float`) · پیش‌فرض · حداقل · حداکثر.
- سقف رابط کاربری: **۲۴** پارامتر.

نام پارامتر را بعداً در «Period param» اندیکاتور و در ارجاع `param` داخل قواعد استفاده کنید.

#### اندیکاتورها (Indicators)

سری‌هایی که در قواعد به آن‌ها ارجاع می‌دهید.

| فیلد | معنی |
|------|------|
| **Id** | شناسهٔ کوتاه در قواعد (مثل `fast`, `rsi`) |
| **Fn** | `sma`, `ema`, `rsi`, `atr`, `macd`, `bollinger` |
| **Source** | `primary` = تایم‌فریم استراتژی · `htf` = تایم‌فریم بالاتر |
| **Period** | دورهٔ ثابت عددی |
| **Period param** | یا اتصال دوره به نام یک پارامتر (برای تیون بهتر) |
| **Column** | فیلد قیمت (`close` پیش‌فرض؛ برای سقف/کف رنج از `high`/`low`) |

- از **۱ ردیف** شروع؛ **+ Add indicator** / **−**.
- سقف: **۱۶** اندیکاتور.

اگر حتی یک اندیکاتور **HTF** باشد، در بک‌تست و دیپلوی انتخاب تایم‌فریم بالاتر **اجباری** است.

#### گروه‌های ورود / خروج

چهار گروه: **Entry long** · **Entry short** · **Exit long** · **Exit short**.

هر گروه:

- **Logic**: بین قواعد همان گروه `AND` یا `OR`.
- هر قاعده: **Left** *عملگر* **Right**.
- **+ Add rule** / **−** (سقف **۱۲** قاعده در هر گروه).

**عملگرها:** `>`, `>=`, `<`, `<=`, `==`, `cross_above`, `cross_below`.

**انواع ارجاع Left / Right:**

| نوع | کاربرد |
|-----|--------|
| **indicator** | شناسهٔ اندیکاتور |
| **price** | open / high / low / close |
| **value** | عدد ثابت |
| **param** | نام پارامتر |
| **pct_offset** | پایه ± درصد (یک سطح تو در تو) |
| **arith** | `+ − * /` روی دو ارجاع ساده (یک سطح) |

**ترتیب ارزیابی در هر کندل:** اول خروج → بعد ورود خرید → بعد ورود فروش.

#### حد ضرر و حد سود

| حد ضرر (Stop loss) | حد سود (Take profit) |
|--------------------|----------------------|
| هیچ | هیچ |
| **Percent** از نقطهٔ ورود | **Percent** از نقطهٔ ورود |
| **ATR** (ضریب × دوره ATR) | **R:R** (چند برابر فاصلهٔ حد ضرر) |

این مقادیر روی سیگنال ورود برای بک‌تست و لایو می‌نشینند.

### ۴.۳ ویرایش استراتژی قاعده‌محور

در **Saved strategies** برچسب **Rules** → **Edit** همان سازنده را با ردیف‌های پر باز می‌کند. دوباره ذخیره = اعتبارسنجی دوباره.

---

## ۵. استراتژی پایتون سفارشی

### مراحل

1. **Upload custom strategy** (`/strategies/custom/new/`).
2. **Name**، در صورت تمایل **Description**، و کد منبع را بچسبانید.
3. **Validate & save**.

### الزامات

- ارث‌بری از `BaseStrategy`.
- پیاده‌سازی `on_bar(self, ctx)`.
- بهتر است `module_path`, `slug`, `name`, `default_parameters`, `parameter_schema` را تنظیم کنید.
- قبل از ذخیره، import و **dry-run** روی نمونه کندل انجام می‌شود.
- فایل‌ها در `apps/strategies/user/` ذخیره می‌شوند.

### ویرایش

برچسب **Python** → **Edit** کد را درجا به‌روز و دوباره اعتبارسنجی می‌کند.

### اسکچ حداقلی

```python
from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.signals import Signal, SignalAction

class MyStrategy(BaseStrategy):
    slug = "my_strategy"
    name = "My strategy"
    module_path = "apps.strategies.user.will_be_set_on_install"
    default_parameters = {"period": 14}
    parameter_schema = [
        {"name": "period", "type": "int", "min": 2, "max": 100, "default": 14},
    ]

    def on_bar(self, ctx: BarContext) -> Signal | None:
        return None
```

---

## ۶. مدیریت ذخیره‌شده‌ها

| عمل | رفتار |
|-----|--------|
| **Edit** | قواعد → سازنده · پایتون → ویرایشگر کد · کتابخانه → فرم پارامتر |
| **Duplicate** | کپی با نام/اسلاگ جدید؛ ویرایشگر کلون باز می‌شود |
| **Delete** | صفحهٔ تأیید. اگر بک‌تست یا دیپلوی به استراتژی وصل باشد **حذف ممنوع** است |

---

## ۷. بعد از ذخیره — بک‌تست و دیپلوی

### بک‌تست

1. بخش **Backtest** → New backtest.
2. استراتژی، نماد کاتالوگ، تایم‌فریم اصلی و بازهٔ تاریخ را انتخاب کنید.
3. اگر استراتژی **HTF** دارد، تایم‌فریم **بالاتر** را حتماً بگذارید.
4. اجرا کنید و win rate، منحنی سرمایه و معاملات را ببینید.

### دیپلوی (دمو / واقعی MT5)

1. ایجنت ویندوز آنلاین با توکن معتبر.
2. **Trading** → New deployment → استراتژی، ایجنت، نگاشت نماد، تایم‌فریم، حجم لات.
3. صفحهٔ مرور، پارامترها و آخرین بک‌تست هم‌خوان (اگر باشد) را نشان می‌دهد.
4. **Arm deployment** — ایجنت استراتژی را می‌گیرد و روی هر کندل جدید اجرا می‌کند.

مسیر اجرا همان `on_bar` / موتور قواعد بک‌تست است.

---

## ۸. محدودیت‌ها و نکته‌ها

| موضوع | توضیح |
|-------|--------|
| تعداد پارامتر در سازنده | تا ۲۴ با **+**؛ شروع از ۱ |
| اندیکاتور / قاعده در UI | تا ۱۶ اندیکاتور؛ ۱۲ قاعده در هر گروه |
| عبارات تو در تو | فقط یک سطح `pct_offset` / `arith` |
| HTF | هر اندیکاتور با `source=htf` → HTF در بک‌تست/دیپلوی اجباری |
| حذف | اول بک‌تست‌ها/دیپلوی‌های وابسته را پاک یا رها کنید |
| کتابخانه در برابر قواعد | ایدهٔ مشابه؛ یکی پایتون ثابت، یکی JSON قابل ویرایش |
| دستور seed | بعد از pull دوباره seed بزنید تا کارت‌ها/قالب‌ها تازه شوند |

---

## ۹. دستورهای سریع

**تقاطع میانگین بدون کد**  
قالب *MA cross (rules)* → دوره‌ها را تنظیم → ذخیره → بک‌تست M5 (برای فیلتر HTF از قالب *MA cross + HTF filter* با مثلاً H1).

**تیون RSI کتابخانه**  
Library → *RSI reversal* → Configure → oversold/overbought → Save → Backtest.

**ایدهٔ سفارشی**  
آپلود پایتون با `BaseStrategy` → Validate & save → بک‌تست → وقتی آماده بود Deploy.
