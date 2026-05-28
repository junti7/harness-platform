"""Generate chart assets for Physical AI Weekly issues.

Outputs:
- docs/issues/<name>.png      (rendered chart)
- docs/issues/<name>.b64      (base64 text, consumed by render_markdown_pdf.py)

Run: .venv/bin/python scripts/generate_charts.py
"""
from __future__ import annotations

import base64
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

ISSUES_DIR = Path("/Users/juntae.park/projects/harness-platform/docs/issues")

PRIMARY = "#2563eb"
GREEN = "#10b981"
RED = "#ef4444"
INK = "#111827"
SUB = "#374151"
GRID = "#e5e7eb"
MUTED = "#9ca3af"

plt.rcParams.update({
    "font.family": ["AppleGothic", "Apple SD Gothic Neo", "Helvetica Neue", "sans-serif"],
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def _save(fig: plt.Figure, name: str) -> None:
    png_path = ISSUES_DIR / f"{name}.png"
    fig.savefig(png_path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    b64 = base64.b64encode(png_path.read_bytes()).decode("utf-8")
    (ISSUES_DIR / f"{name}.b64").write_text(b64)
    print(f"saved: {png_path.name} + {name}.b64 ({len(b64):,} chars)")


def cost_trend_chart() -> None:
    """§1 Cost Trend: actuator / LiDAR / AI inference cost decline 2020–2025.

    Sources cited in issue body:
      - ARK Big Ideas 2024 (Wright's Law, robotics hardware)
      - McKinsey "Economic Potential of Generative AI" 2023
      - SemiAnalysis inference cost benchmarks 2023
    Decline rates from issue body:
      - Actuator: ~30%/yr
      - LiDAR:    ~30%/yr (5yr CAGR)
      - AI infer: ~86%/yr
    """
    years = np.arange(2020, 2026)
    actuator = 100 * (1 - 0.30) ** (years - 2020)
    lidar = 100 * (1 - 0.30) ** (years - 2020) * 0.92  # offset to avoid overlap
    inference = 100 * (1 - 0.86) ** (years - 2020)

    fig, ax = plt.subplots(figsize=(11, 8), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    series = [
        ("정밀 액추에이터", actuator, PRIMARY, 1.18),
        ("라이다(LiDAR)", lidar, GREEN, 0.78),
        ("AI 추론 비용", inference, RED, 1.0),
    ]
    for label, data, color, label_yshift in series:
        ax.plot(
            years, data,
            color=color, linewidth=4,
            marker="o", markersize=11,
            markeredgecolor="white", markeredgewidth=2.2,
            label=label, zorder=3,
        )
        ax.text(
            years[-1] + 0.12, data[-1] * label_yshift, label,
            color=color, fontsize=13, fontweight="bold", va="center",
        )

    ax.set_yscale("log")
    ax.set_ylim(0.0008, 220)
    ax.set_xlim(2019.6, 2027.0)

    ax.set_xlabel("Year", fontsize=13, fontweight="bold", color=SUB, labelpad=12)
    ax.set_ylabel("Cost Index  (2020 = 100, log scale)", fontsize=13, fontweight="bold", color=SUB, labelpad=12)
    ax.set_title(
        "Robotics Hardware & AI Inference Cost Decline",
        fontsize=22, fontweight="900", color=INK, pad=38, loc="left",
    )
    ax.text(
        0.0, 1.04, "2020-2025  |  Wright's Law trajectory",
        transform=ax.transAxes, fontsize=12, color=MUTED, fontweight="600",
    )

    ax.grid(True, which="major", linestyle="-", linewidth=0.8, color=GRID, zorder=0)
    ax.grid(True, which="minor", linestyle=":", linewidth=0.5, color="#f3f4f6", zorder=0)

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
        ax.spines[s].set_linewidth(1.4)

    ax.tick_params(axis="both", labelsize=11, colors=SUB)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_formatter(ticker.NullFormatter())

    # callout: AI inference 86% decline
    ax.annotate(
        "-86% / yr",
        xy=(2024, inference[4]), xytext=(2022.3, 0.004),
        fontsize=12, fontweight="bold", color=RED,
        arrowprops=dict(arrowstyle="->", color=RED, lw=1.6),
    )

    fig.text(
        0.02, -0.02,
        "Source: ARK Big Ideas 2024, McKinsey (2023), SemiAnalysis (2023). "
        "Index normalized to 2020 = 100; rates derived from cited cost-decline figures.",
        fontsize=9, color=MUTED, style="italic",
    )

    plt.tight_layout()
    _save(fig, "robotics_cost")


def concept_diagram() -> None:
    """§2 Concept: [Intelligence] x [Action] = [Generalization] flow diagram.

    Visual metaphor for the body claim that multimodal LLM reasoning combined
    with precise physical actuation yields generalizable robotics. No
    photographic or generative-AI imagery — pure structural diagram so QA can
    fact-check every label against the issue body.
    """
    fig, ax = plt.subplots(figsize=(11, 8), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def box(x, y, w, h, title, sub, color):
        rect = plt.Rectangle(
            (x, y), w, h,
            facecolor="white", edgecolor=color, linewidth=3.2,
            zorder=2,
        )
        ax.add_patch(rect)
        # color bar at top of card
        ax.add_patch(plt.Rectangle((x, y + h - 4), w, 4, facecolor=color, edgecolor="none", zorder=3))
        ax.text(x + w / 2, y + h - 9, title, ha="center", va="top",
                fontsize=15, fontweight="900", color=INK, zorder=4)
        ax.text(x + w / 2, y + h - 18, sub, ha="center", va="top",
                fontsize=10, color=SUB, zorder=4, linespacing=1.55)

    # Top row: Intelligence x Action = Generalization
    box(4, 56, 24, 34, "멀티모달 LLM", "자연어 추론\n장기 계획\nSim-to-Real", PRIMARY)
    box(38, 56, 24, 34, "정밀 액추에이터", "고토크 모터\nLiDAR / 비전\nOn-device 추론", GREEN)
    box(72, 56, 24, 34, "범용 휴머노이드", "비구조 환경\n다목적 작업\n소프트웨어 업데이트", RED)

    # Operators between boxes
    ax.text(33, 73, "×", ha="center", va="center", fontsize=42, color=INK, fontweight="900")
    ax.text(67, 73, "=", ha="center", va="center", fontsize=42, color=INK, fontweight="900")

    # Bottom: outcome callout
    ax.add_patch(plt.Rectangle((4, 18), 92, 28, facecolor="#f9fafb",
                               edgecolor=GRID, linewidth=2, zorder=1))
    ax.text(50, 38, "Generalizable Robotics", ha="center", va="center",
            fontsize=22, fontweight="900", color=INK)
    ax.text(50, 26, "구조화된 공장 라인  →  비구조적 일상 환경",
            ha="center", va="center", fontsize=14, color=SUB, fontweight="600")

    # Top-left title
    ax.text(2, 96, "Convergence Architecture",
            fontsize=20, fontweight="900", color=INK)
    ax.text(2, 92, "Physical AI = Reasoning x Embodiment",
            fontsize=12, color=MUTED, fontweight="600")

    # Down arrows
    for x in (16, 50, 84):
        ax.annotate("", xy=(x, 47), xytext=(x, 55),
                    arrowprops=dict(arrowstyle="->", color=MUTED, lw=2))

    fig.text(0.02, 0.02,
             "Source: Issue body §2; ARK Big Ideas 2024; McKinsey 2023.",
             fontsize=9, color=MUTED, style="italic")

    plt.tight_layout()
    _save(fig, "concept_robot")


def tam_breakdown_chart() -> None:
    """§3 TAM: 2030 economic value breakdown — Manufacturing $12T + Domestic $12.5T = $24.5T+.

    Body figures (issue §3):
      - Manufacturing productivity: $12T/yr
      - Domestic-labor monetization: $12.5T/yr
      - Total addressable: $24T+ /yr
      - Operating-margin gap (platform vs non-platform): 30 pp
    """
    fig = plt.figure(figsize=(11, 8), dpi=220)
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(2, 1, height_ratios=[1.4, 1.0], hspace=0.55)

    # ---- Top: stacked horizontal bar showing TAM composition ----
    ax_top = fig.add_subplot(gs[0])
    ax_top.set_facecolor("white")

    mfg = 12.0
    dom = 12.5
    total = mfg + dom

    ax_top.barh([0], [mfg], color=PRIMARY, edgecolor="white", linewidth=2, zorder=3)
    ax_top.barh([0], [dom], left=[mfg], color=GREEN, edgecolor="white", linewidth=2, zorder=3)

    # In-bar labels
    ax_top.text(mfg / 2, 0, f"제조업 생산성\n${mfg:.0f}T",
                ha="center", va="center", color="white",
                fontsize=14, fontweight="900")
    ax_top.text(mfg + dom / 2, 0, f"가사·서비스 노동\n${dom:.1f}T",
                ha="center", va="center", color="white",
                fontsize=14, fontweight="900")

    ax_top.set_xlim(0, total * 1.08)
    ax_top.set_ylim(-0.7, 0.7)
    ax_top.set_yticks([])
    ax_top.set_xlabel("Annual Economic Impact  (USD trillions, 2030)",
                      fontsize=12, fontweight="bold", color=SUB, labelpad=10)
    ax_top.tick_params(axis="x", labelsize=11, colors=SUB)
    ax_top.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v:.0f}T"))

    for s in ("top", "right", "left"):
        ax_top.spines[s].set_visible(False)
    ax_top.spines["bottom"].set_color(MUTED)

    # Total callout
    ax_top.text(total + 0.4, 0, f"= ${total:.1f}T+",
                ha="left", va="center", fontsize=22, fontweight="900", color=INK)

    ax_top.set_title("2030 Total Addressable Market (TAM)",
                     fontsize=22, fontweight="900", color=INK, pad=38, loc="left")
    ax_top.text(0.0, 1.04, "Annual economic impact of generalizable robotics",
                transform=ax_top.transAxes, fontsize=12, color=MUTED, fontweight="600")

    # ---- Bottom: operating-margin gap callout ----
    ax_bot = fig.add_subplot(gs[1])
    ax_bot.set_facecolor("white")
    ax_bot.set_xlim(0, 100)
    ax_bot.set_ylim(0, 50)
    ax_bot.axis("off")

    # Two pill cards
    def pill(x, w, label, value, color, value_color):
        ax_bot.add_patch(plt.Rectangle((x, 8), w, 34, facecolor="white",
                                       edgecolor=color, linewidth=2.5, zorder=2))
        ax_bot.add_patch(plt.Rectangle((x, 38), w, 4, facecolor=color,
                                       edgecolor="none", zorder=3))
        ax_bot.text(x + w / 2, 30, label, ha="center", va="center",
                    fontsize=12, fontweight="bold", color=SUB)
        ax_bot.text(x + w / 2, 18, value, ha="center", va="center",
                    fontsize=22, fontweight="900", color=value_color)

    pill(2, 44, "플랫폼 보유 기업\n(Operating Margin Premium)", "+30pp", PRIMARY, PRIMARY)
    pill(54, 44, "비플랫폼 기업\n(Margin Erosion)", "-30pp", RED, RED)
    ax_bot.text(50, 46, "Operating-Margin Gap by 2030",
                ha="center", va="center", fontsize=13, fontweight="900", color=INK)

    fig.text(0.02, 0.02,
             "Source: ARK Big Ideas 2024; McKinsey 'Economic Potential of Generative AI' (2023). "
             "Figures = annual TAM projection at 2030 horizon.",
             fontsize=9, color=MUTED, style="italic")

    _save(fig, "tam_breakdown")


def watchlist_matrix() -> None:
    """§4 Watchlist: Beneficiaries vs At-Risk segments by 2030.

    Body figures (issue §4):
      - Beneficiaries: robot OS platforms (Nvidia, Tesla),
        precision actuator / harmonic drive makers
      - At Risk:       single-purpose / legacy industrial robot OEMs
      - Margin spread: ~30pp by 2030 (carried from §3)
    """
    fig, ax = plt.subplots(figsize=(11, 8), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def column(x0, header, header_color, header_bg, trend_label, items, item_bg):
        # Outer card
        ax.add_patch(plt.Rectangle((x0, 10), 44, 74,
                                   facecolor="white", edgecolor=header_color, linewidth=3, zorder=2))
        # Header bar
        ax.add_patch(plt.Rectangle((x0, 80), 44, 4,
                                   facecolor=header_color, edgecolor="none", zorder=3))
        # Header text
        ax.text(x0 + 22, 75, header, ha="center", va="center",
                fontsize=14, fontweight="900", color=header_color, zorder=4)
        ax.text(x0 + 22, 69, trend_label, ha="center", va="center",
                fontsize=12, color=header_color, fontweight="bold", zorder=4)

        for idx, (cat, examples) in enumerate(items):
            y_top = 60 - idx * 18
            ax.add_patch(plt.Rectangle((x0 + 2, y_top - 14), 40, 14,
                                       facecolor=item_bg, edgecolor=header_color,
                                       linewidth=1.2, zorder=3))
            ax.text(x0 + 22, y_top - 5, cat, ha="center", va="center",
                    fontsize=11, fontweight="900", color=INK, zorder=4)
            ax.text(x0 + 22, y_top - 11, examples, ha="center", va="center",
                    fontsize=9.5, color=SUB, zorder=4)

    column(
        4,
        "수혜 기업군 (Beneficiaries)", GREEN, "#f0fdf4",
        "▲ Operating Margin  +30pp",
        [
            ("로봇 OS 플랫폼", "Nvidia · Tesla 등"),
            ("정밀 액추에이터", "고토크 모터 · 하모닉 드라이브"),
            ("On-device AI 칩", "추론 비용 -86% / yr"),
        ],
        "#f0fdf4",
    )
    column(
        52,
        "타격 예상 (At Risk)", RED, "#fef2f2",
        "▼ Operating Margin  -30pp",
        [
            ("전용 목적 로봇사", "구형 산업용 robot OEM"),
            ("Non-platform 하드웨어", "범용성 부재 · 마진 압박"),
            ("정체된 공정 자동화", "Sim-to-Real 도입 지연"),
        ],
        "#fef2f2",
    )

    # Top title
    ax.text(2, 96, "Watchlist Matrix",
            fontsize=20, fontweight="900", color=INK)
    ax.text(2, 92, "Operating-margin trajectory by 2030",
            fontsize=12, color=MUTED, fontweight="600")

    fig.text(0.02, 0.02,
             "Source: Issue body §4; ARK Big Ideas 2024. "
             "Examples are illustrative; not investment advice.",
             fontsize=9, color=MUTED, style="italic")

    plt.tight_layout()
    _save(fig, "watchlist")


def edu_parent_readiness_chart() -> None:
    """Customer education sample: parents-first AI readiness gap.

    Synthetic example for customer-facing education visual sample.
    Message:
      - awareness is already high
      - household standards and parent weekly usage are still low
      - therefore "parents first, children later" training is justified
    """
    labels = [
        "AI가 중요하다고 느낀다",
        "자녀 교육에 AI가 필요하다고 느낀다",
        "우리 집 AI 사용 기준이 있다",
        "부모가 매주 직접 AI를 써본다",
    ]
    values = np.array([88, 81, 39, 27])
    colors = [PRIMARY, PRIMARY, GREEN, RED]
    ypos = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(11, 8), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    bars = ax.barh(ypos, values, color=colors, height=0.6, zorder=3)
    ax.set_xlim(0, 100)
    ax.set_yticks(ypos, labels=labels)
    ax.invert_yaxis()

    ax.set_title(
        "학부모 AI 인식은 높지만 실행 기준은 아직 낮다",
        fontsize=22, fontweight="900", color=INK, pad=38, loc="left",
    )
    ax.text(
        0.0, 1.04, "Parents-first education sample  |  awareness vs. household operating standard",
        transform=ax.transAxes, fontsize=12, color=MUTED, fontweight="600",
    )

    ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
    ax.xaxis.set_major_formatter(ticker.PercentFormatter())
    ax.grid(True, axis="x", color=GRID, linewidth=0.9, zorder=0)

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(axis="y", labelsize=13, colors=SUB, length=0)
    ax.tick_params(axis="x", labelsize=11, colors=SUB)

    for rect, value in zip(bars, values):
        ax.text(
            min(value + 2.2, 96),
            rect.get_y() + rect.get_height() / 2,
            f"{value}%",
            va="center",
            ha="left",
            fontsize=13,
            fontweight="bold",
            color=INK,
        )

    ax.annotate(
        "인식과 실행 사이의 격차가 상품의 핵심 진입점",
        xy=(39, 2), xytext=(57, 2.8),
        fontsize=12, color=SUB, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=PRIMARY, lw=1.6),
    )

    fig.text(
        0.02, -0.02,
        "Sample asset for customer education consulting. Illustrative percentages for design demonstration only.",
        fontsize=9, color=MUTED, style="italic",
    )

    plt.tight_layout()
    _save(fig, "edu_parent_readiness")


def edu_parents_first_infographic() -> None:
    """Customer education sample infographic: parents first, children later."""
    fig, ax = plt.subplots(figsize=(11, 8), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(4, 95, "부모 먼저, 자녀는 나중", fontsize=24, fontweight="900", color=INK)
    ax.text(4, 89, "AI 시대 가정 학습 기준을 만드는 3-step 교육 흐름", fontsize=12, color=MUTED, fontweight="600")

    cards = [
        (6, 26, 25, 48, PRIMARY, "1", "부모가 먼저 AI를 직접 써본다", "도구 체험\n업무/일상 적용\n실패 포인트 기록"),
        (37.5, 26, 25, 48, GREEN, "2", "우리 집 사용 기준을 만든다", "허용/금지 선 정리\n시간 기준 설정\n질문 방식 통일"),
        (69, 26, 25, 48, RED, "3", "그 기준으로 자녀 원칙을 설계한다", "학년별 사용 규칙\n대화 가이드\n주간 점검 루틴"),
    ]

    for x, y, w, h, color, num, title, body in cards:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="white", edgecolor=color, linewidth=3.0, zorder=2))
        ax.add_patch(plt.Rectangle((x, y + h - 5), w, 5, facecolor=color, edgecolor="none", zorder=3))
        ax.text(x + 3, y + h - 10, num, fontsize=21, fontweight="900", color=color, va="top")
        ax.text(x + 3, y + h - 18, title, fontsize=14, fontweight="900", color=INK, va="top")
        ax.text(x + 3, y + h - 29, body, fontsize=11, color=SUB, va="top", linespacing=1.55)

    for x1, x2 in ((31.5, 37.5), (63, 69)):
        ax.annotate("", xy=(x2 - 1.2, 50), xytext=(x1 + 1.2, 50),
                    arrowprops=dict(arrowstyle="->", lw=2.0, color=MUTED))

    ax.add_patch(plt.Rectangle((6, 8), 88, 12, facecolor="#f8fafc", edgecolor=GRID, linewidth=1.8))
    ax.text(50, 14, "핵심 메시지: 부모가 기준을 체험 없이 만들지 못하면 자녀 AI 교육은 공허해진다",
            ha="center", va="center", fontsize=13, fontweight="bold", color=SUB)

    fig.text(
        0.02, 0.02,
        "Sample infographic for customer education consulting. Final Korean copy should be post-edited before client delivery.",
        fontsize=9, color=MUTED, style="italic",
    )

    plt.tight_layout()
    _save(fig, "edu_parents_first_infographic")


def edu_parent_action_flashcard() -> None:
    """Customer education sample flashcard: 3 actions this week."""
    fig, ax = plt.subplots(figsize=(11, 8), dpi=220)
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.add_patch(plt.Rectangle((6, 8), 88, 84, facecolor="white", edgecolor=GRID, linewidth=2.2))
    ax.add_patch(plt.Rectangle((6, 82), 88, 10, facecolor=PRIMARY, edgecolor="none"))
    ax.text(10, 86.5, "이번 주 부모가 먼저 해볼 것 3가지", fontsize=20, fontweight="900", color="white", va="center")
    ax.text(10, 74, "AI 교육은 정보 습득보다 부모의 직접 체험에서 시작됩니다.", fontsize=13, color=MUTED, fontweight="600")

    actions = [
        ("1", "ChatGPT에 실제 질문 1개 해보기", "내 업무/가정에서 지금 바로 필요한 질문으로 시작"),
        ("2", "자녀와 AI 사용에 대해 10분 대화하기", "통제보다 관찰과 질문으로 시작"),
        ("3", "우리 집 AI 허용/금지 기준 1줄 쓰기", "예: 숙제 초안은 가능, 최종 답안 대필은 금지"),
    ]

    y = 58
    for num, title, desc in actions:
        ax.add_patch(plt.Circle((13, y + 2), 3.6, color=PRIMARY))
        ax.text(13, y + 2, num, ha="center", va="center", fontsize=12, fontweight="900", color="white")
        ax.text(19, y + 5, title, fontsize=15, fontweight="900", color=INK, va="top")
        ax.text(19, y - 1, desc, fontsize=11.5, color=SUB, va="top")
        y -= 18

    ax.add_patch(plt.Rectangle((10, 13), 80, 9, facecolor="#eff6ff", edgecolor="none"))
    ax.text(50, 17.5, "Takeaway: 부모가 먼저 기준을 가져야 자녀에게도 일관된 원칙을 줄 수 있습니다.",
            ha="center", va="center", fontsize=12, color=PRIMARY, fontweight="bold")

    fig.text(
        0.02, 0.02,
        "Sample flashcard for adult parent education clients. Reusable card template for post-session follow-up.",
        fontsize=9, color=MUTED, style="italic",
    )

    plt.tight_layout()
    _save(fig, "edu_parent_action_flashcard")


if __name__ == "__main__":
    cost_trend_chart()
    concept_diagram()
    tam_breakdown_chart()
    watchlist_matrix()
    edu_parent_readiness_chart()
    edu_parents_first_infographic()
    edu_parent_action_flashcard()
