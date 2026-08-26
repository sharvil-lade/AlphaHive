from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    email: EmailStr
    # Upper bound is a DoS guard: bcrypt cost is fixed, but hashing an unbounded body
    # still costs bandwidth and memory. Lower bound is the usual minimum.
    password: str = Field(..., min_length=8, max_length=128)
    name: Optional[str] = Field(None, max_length=120)

    @field_validator("password")
    @classmethod
    def password_not_trivial(cls, v: str) -> str:
        if v.strip() != v:
            raise ValueError("Password must not start or end with whitespace.")
        if v.lower() in {"password", "12345678", "qwertyui", "11111111"}:
            raise ValueError("That password is too common. Pick something less guessable.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)


class SessionResponse(BaseModel):
    """The client's view of who it is. Never exposes the raw session id — that lives
    only in the httpOnly cookie, so JavaScript (and any XSS) cannot read it."""

    authenticated: bool
    user_id: Optional[UUID] = None
    email: Optional[str] = None
    name: Optional[str] = None



# Stock Schemas
class StockBase(BaseModel):
    symbol: str = Field(..., max_length=10, description="Stock Ticker Symbol")
    name: str = Field(..., description="Company Name")
    sector: Optional[str] = None
    industry: Optional[str] = None


class StockCreate(StockBase):
    pass


class StockSchema(StockBase):
    class Config:
        from_attributes = True


# Stock Price Schemas
class StockPriceBase(BaseModel):
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockPriceCreate(StockPriceBase):
    pass


class StockPriceSchema(StockPriceBase):
    id: UUID

    class Config:
        from_attributes = True


# Portfolio Holding Schemas
class PortfolioHoldingBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    shares: float = Field(..., gt=0, le=1e12)
    average_buy_price: float = Field(..., ge=0, le=1e12)


class PortfolioHoldingCreate(PortfolioHoldingBase):
    pass


class PortfolioHoldingUpdate(BaseModel):
    shares: float = Field(..., gt=0, le=1e12)
    average_buy_price: float = Field(..., ge=0, le=1e12)


class PortfolioHoldingSchema(PortfolioHoldingBase):
    id: UUID
    portfolio_id: UUID
    last_updated: datetime

    class Config:
        from_attributes = True


# Portfolio Schemas
class PortfolioBase(BaseModel):
    name: str


class PortfolioCreate(BaseModel):
    name: str


class PortfolioSchema(PortfolioBase):
    id: UUID
    created_at: datetime
    holdings: List[PortfolioHoldingSchema] = []

    class Config:
        from_attributes = True


class PortfolioSummaryHolding(BaseModel):
    id: str
    portfolio_id: str
    symbol: str
    shares: float
    average_buy_price: float
    current_price: float
    total_value: float
    total_cost: float
    gain_loss: float
    gain_loss_percentage: float
    sector: str
    beta: float
    volatility: float
    last_updated: Optional[str] = None


class PortfolioSummaryResponse(BaseModel):
    portfolio_id: str
    name: str
    total_value: float
    total_cost: float
    gain_loss: float
    gain_loss_percentage: float
    weighted_beta: float
    weighted_volatility: float
    holdings: List[PortfolioSummaryHolding]
    sector_weights: Dict[str, float]


class GrowwImportRequest(BaseModel):
    """Import holdings via the official Groww Trade API using a daily access token."""
    access_token: str
    replace: bool = True


class PortfolioImportResult(BaseModel):
    imported: int
    replaced: bool
    portfolio_id: str
    message: str



# Watchlist Schemas
class WatchlistCreate(BaseModel):
    symbol: str


class WatchlistSchema(BaseModel):
    id: UUID
    session_id: str
    symbol: str
    created_at: datetime

    class Config:
        from_attributes = True


# Alert Schemas
class AlertCreate(BaseModel):
    symbol: str
    trigger_type: str = Field(..., description="Trigger Type: rsi_below, rsi_above, sentiment_drop, price_above, price_below")
    trigger_value: float


class AlertSchema(AlertCreate):
    id: UUID
    session_id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Quote and News API Schemas
class QuoteResponse(BaseModel):
    symbol: str
    price: float
    change: float
    percent_change: float
    high: float
    low: float
    open: float
    previous_close: float
    source: str


class NewsResponse(BaseModel):
    symbol: str
    headline: str
    summary: str
    url: str
    source: str
    published_at: str


# Investment Report Schemas
class InvestmentReportSchema(BaseModel):
    id: UUID
    run_id: UUID
    ticker: str
    recommendation: str
    confidence_score: int
    content_markdown: str
    created_at: datetime

    class Config:
        from_attributes = True


# Agent Run Schemas
class AgentRunBase(BaseModel):
    session_id: str
    ticker: str


class AgentRunSchema(AgentRunBase):
    id: UUID
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    report: Optional[InvestmentReportSchema] = None

    class Config:
        from_attributes = True


# Orchestration Schemas (Request/Response)
class ResearchQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language stock research query (e.g. Should I buy NVDA?)")


class AgentExecutionLog(BaseModel):
    node: str
    message: str
    timestamp: datetime


class AgentRunDetailResponse(BaseModel):
    run_id: UUID
    ticker: str
    status: str
    logs: List[AgentExecutionLog] = []
    report: Optional[InvestmentReportSchema] = None
    telemetry: Dict[str, Any] = {}


# Technical Indicators scoring schemas
class SignalDetail(BaseModel):
    score: int
    signal: str


class TASignals(BaseModel):
    rsi: SignalDetail
    macd: SignalDetail
    trends: SignalDetail
    bollinger: SignalDetail
    volume: SignalDetail


class PivotDetails(BaseModel):
    pivot: float
    r1: float
    s1: float
    r2: float
    s2: float


class TechnicalPostureResponse(BaseModel):
    symbol: str
    close: float
    score: int
    rating: str
    signals: TASignals
    summary: str
    pivots: Optional[PivotDetails] = None


class SentimentResponse(BaseModel):
    symbol: str
    score: int
    rating: str
    summary: str
    opportunities: List[str]
    threats: List[str]
    source: str


class IndexResponse(BaseModel):
    symbol: str
    form_type: str
    status: str
    chunks_indexed: int


class SearchChunkDetail(BaseModel):
    text: str
    section: str
    chunk_id: int
    score: float


class QueryResponse(BaseModel):
    symbol: str
    query: str
    matches: List[SearchChunkDetail]


class ReportHistoryItem(BaseModel):
    run_id: UUID
    ticker: str
    status: str
    recommendation: str
    confidence_score: int
    created_at: str


# Backtesting Schemas
class BacktestRequest(BaseModel):
    symbol: str
    strategy: str = Field("rsi", description="Strategy type: rsi, ema_crossover, macd_crossover")
    initial_capital: float = Field(10000.0, description="Initial portfolio cash amount")
    range_str: str = Field("1y", description="Historical duration range (e.g. 1mo, 3mo, 6mo, 1y)")


class EquityPoint(BaseModel):
    date: str
    portfolio_value: float
    benchmark_value: float


class BacktestTrade(BaseModel):
    type: str
    date: str
    price: float
    shares: float
    value: float
    cash_remaining: float
    profit_loss: float
    profit_loss_pct: float


class BacktestResponse(BaseModel):
    symbol: str
    strategy: str
    initial_capital: float
    final_value: float
    total_return: float
    benchmark_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    equity_curve: List[EquityPoint]
    trades: List[BacktestTrade]


# Chat Schemas
class ConversationCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)


class ConversationUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class ConversationSchema(BaseModel):
    id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentTraceSchema(BaseModel):
    id: UUID
    node: str
    status: str
    summary: Optional[str] = None
    label: Optional[str] = None
    rating: Optional[str] = None
    confidence: Optional[int] = None
    started_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageSchema(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    status: str
    created_at: datetime
    traces: List[AgentTraceSchema] = []

    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationSchema):
    messages: List[MessageSchema] = []


class ChatMessageCreate(BaseModel):
    # Bounded so a single request can't push an unbounded prompt into the LLM (cost)
    # or the messages table (storage).
    content: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Free-form natural language query, e.g. 'Should I buy Reliance right now?'",
    )


class ChatMessageCreateResponse(BaseModel):
    user_message: MessageSchema
    assistant_message: MessageSchema


