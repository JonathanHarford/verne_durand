# Context7: Claude Skills System

The Claude Skills System is a framework for extending Claude's capabilities through modular, self-contained instruction packages. Skills are folders containing structured documentation, scripts, and resources that Claude dynamically loads to perform specialized tasks. Each skill provides procedural knowledge, domain expertise, and reusable assets that enable Claude to execute specific workflows more effectively - from creating documents to integrating external APIs.

Skills follow a progressive disclosure model where metadata determines discoverability, the SKILL.md file provides core instructions, and optional bundled resources (scripts, references, assets) are loaded on-demand. This architecture maximizes context efficiency while ensuring Claude has access to the specialized knowledge needed for complex, domain-specific tasks. The system supports diverse use cases including document generation and co-authoring, web application testing, API integration via MCP servers, creative design workflows, and enterprise communications.

## Skill Structure Specification

### Basic Skill Folder Layout

```
my-skill/
  └── SKILL.md (required)
```

### Complete Skill with Resources

```
my-skill/
  ├── SKILL.md (required)
  ├── scripts/       (executable code)
  ├── references/    (documentation for context)
  └── assets/        (output resources)
```

### SKILL.md Format

```markdown
---
name: skill-name
description: Clear description of what the skill does and when to use it
license: Optional license information
allowed-tools: Optional pre-approved tool list
metadata: Optional key-value pairs
---

# Skill Title

[Markdown instructions for Claude]
```

## Skill Creation Workflow

### Initialize New Skill

```bash
# Create skill from template
python skills/skill-creator/scripts/init_skill.py my-new-skill --path skills/

# Creates:
# skills/my-new-skill/
#   ├── SKILL.md (with TODO placeholders)
#   ├── scripts/ (example script)
#   ├── references/ (example reference)
#   └── assets/ (example asset)
```

### Validate and Package Skill

```bash
# Validate skill structure and requirements
python skills/skill-creator/scripts/quick_validate.py path/to/my-skill

# Package into distributable zip (includes validation)
python skills/skill-creator/scripts/package_skill.py path/to/my-skill
# Output: my-skill.zip

# Specify custom output directory
python skills/skill-creator/scripts/package_skill.py path/to/my-skill ./dist
# Output: dist/my-skill.zip
```

### Install Skill in Claude Code

```bash
# Register skills marketplace
/plugin marketplace add anthropics/skills

# Use skill by mentioning it
# "use the pdf skill to extract tables from report.pdf"
```

## Document Skills: PDF Processing

### Extract Text and Tables from PDF

```python
import pdfplumber
import pandas as pd

# Extract text preserving layout
with pdfplumber.open("report.pdf") as pdf:
    full_text = ""
    for page in pdf.pages:
        full_text += page.extract_text() + "\n\n"

# Extract all tables to Excel
all_tables = []
with pdfplumber.open("financial_report.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table:  # Skip empty tables
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

# Combine and export
combined_df = pd.concat(all_tables, ignore_index=True)
combined_df.to_excel("extracted_data.xlsx", index=False)
```

### Merge, Split, and Rotate PDFs

```python
from pypdf import PdfReader, PdfWriter

# Merge multiple PDFs
writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)

# Split PDF into individual pages
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)

# Rotate pages
reader = PdfReader("input.pdf")
writer = PdfWriter()
page = reader.pages[0]
page.rotate(90)  # 90 degrees clockwise
writer.add_page(page)
with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### Create PDF with Content

```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

# Add content
title = Paragraph("Q4 2024 Financial Report", styles['Title'])
story.append(title)
story.append(Spacer(1, 12))

body_text = """Revenue grew 15% year-over-year to $2.5M.
Operating expenses decreased 8% while maintaining service quality."""
body = Paragraph(body_text, styles['Normal'])
story.append(body)
story.append(PageBreak())

# Add second page
story.append(Paragraph("Regional Breakdown", styles['Heading1']))
story.append(Paragraph("North America: $1.2M (+12%)", styles['Normal']))
story.append(Paragraph("Europe: $0.9M (+20%)", styles['Normal']))
story.append(Paragraph("Asia-Pacific: $0.4M (+15%)", styles['Normal']))

doc.build(story)
```

## Document Skills: Excel/XLSX Processing

### Create Excel with Formulas and Formatting

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
sheet = wb.active
sheet.title = "Q4 Sales"

# Headers with formatting
sheet['A1'] = 'Product'
sheet['B1'] = 'Units Sold'
sheet['C1'] = 'Revenue'
sheet['D1'] = 'Growth %'

header_font = Font(bold=True, color='FFFFFF')
header_fill = PatternFill('solid', start_color='0066CC')
for cell in ['A1', 'B1', 'C1', 'D1']:
    sheet[cell].font = header_font
    sheet[cell].fill = header_fill
    sheet[cell].alignment = Alignment(horizontal='center')

# Data with color coding (blue = input, black = formula)
sheet['A2'] = 'Widget A'
sheet['B2'] = 1200  # Input: blue text
sheet['B2'].font = Font(color='0000FF')
sheet['C2'] = 48000  # Input: blue text
sheet['C2'].font = Font(color='0000FF')
sheet['D2'] = '=(C2/C$7)-1'  # Formula: black text

sheet['A3'] = 'Widget B'
sheet['B3'] = 850
sheet['B3'].font = Font(color='0000FF')
sheet['C3'] = 34000
sheet['C3'].font = Font(color='0000FF')
sheet['D3'] = '=(C3/C$8)-1'

# Totals with formulas (black text)
sheet['A5'] = 'Total'
sheet['B5'] = '=SUM(B2:B3)'
sheet['C5'] = '=SUM(C2:C3)'

# Format numbers
sheet['C2'].number_format = '$#,##0;($#,##0);-'
sheet['C3'].number_format = '$#,##0;($#,##0);-'
sheet['C5'].number_format = '$#,##0;($#,##0);-'
sheet['D2'].number_format = '0.0%'
sheet['D3'].number_format = '0.0%'

wb.save('sales_report.xlsx')

# CRITICAL: Recalculate formulas
import subprocess
subprocess.run(['python', 'skills/xlsx/recalc.py', 'sales_report.xlsx'], check=True)
```

### Read and Analyze Excel Data

```python
import pandas as pd

# Read specific sheet
df = pd.read_excel('sales_data.xlsx', sheet_name='Q4 Sales')

# Analysis
print(df.head())
print(df.describe())
print(f"Total Revenue: ${df['Revenue'].sum():,.2f}")
print(f"Average Units: {df['Units Sold'].mean():.0f}")

# Load multiple sheets
all_sheets = pd.read_excel('annual_report.xlsx', sheet_name=None)
for sheet_name, df in all_sheets.items():
    print(f"\n{sheet_name}: {len(df)} rows")
```

### Edit Existing Excel File

```python
from openpyxl import load_workbook

# Load preserving formulas and formatting
wb = load_workbook('financial_model.xlsx')
sheet = wb['Projections']

# Modify specific cells
sheet['B10'] = 0.15  # Update growth assumption (blue text)
sheet['B10'].font = Font(color='0000FF')

# Add new calculated column
sheet['F1'] = 'Margin %'
for row in range(2, sheet.max_row + 1):
    sheet[f'F{row}'] = f'=E{row}/D{row}'  # Formula (black text)

# Insert row and copy formulas
sheet.insert_rows(5)
sheet['A5'] = 'New Product Line'
sheet['B5'] = 500
sheet['C5'] = '=B5*$B$2'  # Reference assumption cell

wb.save('financial_model_updated.xlsx')

# CRITICAL: Recalculate all formulas
subprocess.run(['python', 'skills/xlsx/recalc.py', 'financial_model_updated.xlsx'], check=True)
```

## Document Co-Authoring Workflow

### Interactive Document Creation

The doc-coauthoring skill provides a structured three-stage workflow for creating high-quality documentation with Claude. This workflow is optimized for technical specs, decision documents, proposals, and other structured content that needs to work well for readers.

```python
# Example usage: Mention the workflow when starting a documentation task
# "I need to write a technical design doc for our new authentication system"

# Claude will guide through three stages:
# 1. Context Gathering - Transfer all relevant context through Q&A
# 2. Refinement & Structure - Build each section iteratively
# 3. Reader Testing - Verify the doc works for fresh readers
```

### Stage 1: Context Gathering

```markdown
The workflow starts by understanding:
- Document type and audience
- Desired impact when someone reads it
- Template or format requirements
- Background context and related discussions

Claude asks clarifying questions and helps you dump all relevant context
efficiently - from team channels, shared docs, or stream-of-consciousness.
```

### Stage 2: Refinement & Structure

```markdown
For each section of the document:
1. Ask clarifying questions about what to include
2. Brainstorm 5-20 potential points to cover
3. User curates what to keep/remove/combine
4. Draft the section based on selections
5. Refine through surgical edits based on feedback

The workflow learns your style and preferences as you refine each section,
applying that knowledge to subsequent sections.
```

### Stage 3: Reader Testing

```markdown
Test the document with a fresh Claude instance (no context bleed):
1. Predict questions readers might ask
2. Test if Reader Claude can answer them correctly
3. Check for ambiguities and false assumptions
4. Fix any gaps or unclear sections

This catches blind spots - things that make sense to authors but might
confuse readers who don't have the same context.
```

**Key Benefits:**
- Ensures documentation works for readers, not just authors
- Systematic approach prevents missing important context
- Iterative refinement maintains quality throughout
- Reader testing catches issues before human review

## Document Skills: Word/DOCX Processing

### Read and Extract DOCX Content

```bash
# Convert document to markdown with tracked changes
pandoc --track-changes=all path-to-file.docx -o output.md
# Options: --track-changes=accept/reject/all
```

### Unpack and Inspect DOCX Structure

```bash
# Unpack DOCX to access raw XML
python skills/docx/ooxml/scripts/unpack.py document.docx ./unpacked_docx

# Key files:
# - word/document.xml (main content)
# - word/comments.xml (comments)
# - word/styles.xml (styles and formatting)
```

## Document Skills: PowerPoint/PPTX Processing

### Read and Extract PPTX Content

```bash
# Convert presentation to markdown
python -m markitdown presentation.pptx
```

### Unpack and Inspect PPTX Structure

```bash
# Unpack PPTX to access raw XML
python skills/pptx/ooxml/scripts/unpack.py presentation.pptx ./unpacked_pptx

# Key files:
# - ppt/presentation.xml (main metadata)
# - ppt/slides/slide{N}.xml (individual slides)
# - ppt/notesSlides/notesSlide{N}.xml (speaker notes)
# - ppt/theme/theme1.xml (colors and fonts)
```

## Web Application Testing Skill

### Test Dynamic Web Application

```python
# Step 1: Create automation script (test_app.py)
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Navigate and wait for JavaScript to execute
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')

    # Take reconnaissance screenshot
    page.screenshot(path='/tmp/app_loaded.png', full_page=True)

    # Interact with elements
    page.locator('button:has-text("Sign In")').click()
    page.fill('input[name="email"]', 'test@example.com')
    page.fill('input[name="password"]', 'password123')
    page.locator('button[type="submit"]').click()

    # Verify result
    page.wait_for_selector('text=Welcome back')
    page.screenshot(path='/tmp/logged_in.png')

    # Capture console logs for debugging
    page.on('console', lambda msg: print(f'[Console] {msg.text}'))

    browser.close()

# Step 2: Run with server lifecycle management
# python skills/webapp-testing/scripts/with_server.py --server "npm run dev" --port 5173 -- python test_app.py
```

### Test Multiple Servers (Backend + Frontend)

```bash
# Run backend and frontend together, then execute test
python skills/webapp-testing/scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python integration_test.py
```

### Test Static HTML

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Load local HTML file
    page.goto('file:///path/to/index.html')

    # Discover available buttons
    buttons = page.locator('button').all()
    print(f"Found {len(buttons)} buttons:")
    for i, button in enumerate(buttons):
        print(f"  {i+1}. {button.text_content()}")

    # Interact and verify
    page.locator('#calculate-button').click()
    result = page.locator('#result').text_content()
    assert result == '42', f"Expected 42, got {result}"

    browser.close()
```

## Web Artifacts Builder Skill

### Initialize and Bundle React Artifact

```bash
# Step 1: Initialize React project with Tailwind + shadcn/ui
bash skills/web-artifacts-builder/scripts/init-artifact.sh my-dashboard
cd my-dashboard

# Generated stack:
# - React 18 + TypeScript + Vite
# - Tailwind CSS 3.4.1 with shadcn theming
# - 40+ pre-installed shadcn/ui components
# - Path aliases (@/) configured
# - Parcel bundler configuration

# Step 2: Develop application (edit src/App.tsx, etc.)
# Edit generated files to build your artifact

# Step 3: Bundle to single HTML file
bash skills/web-artifacts-builder/scripts/bundle-artifact.sh
# Output: bundle.html (self-contained artifact)
```

### Using Bundled Artifact

```typescript
// Example: src/App.tsx with shadcn components
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { useState } from "react"

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <Card className="max-w-md mx-auto">
        <CardHeader>
          <CardTitle>Counter Dashboard</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-2xl font-bold">{count}</p>
          <Button onClick={() => setCount(count + 1)}>
            Increment
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

export default App
```

After bundling, share bundle.html as a claude.ai artifact. Avoid excessive centered layouts, purple gradients, and Inter font to prevent "AI slop" appearance.

## MCP Server Builder Skill

### Create Python MCP Server (FastMCP)

```python
# weather_server.py - Example MCP server using FastMCP
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field
import httpx

# Server initialization
mcp = Server("weather-server")

# Input validation with Pydantic
class WeatherInput(BaseModel):
    location: str = Field(description="City name (e.g., 'San Francisco' or 'London, UK')")
    units: str = Field(default="imperial", description="Units: 'imperial' (°F) or 'metric' (°C)")

    model_config = {"extra": "forbid"}

# Tool implementation
@mcp.tool()
async def get_weather(location: str, units: str = "imperial") -> str:
    """
    Get current weather for a location.

    Args:
        location: City name (e.g., 'San Francisco' or 'London, UK')
        units: 'imperial' for Fahrenheit, 'metric' for Celsius

    Returns:
        Current weather conditions as formatted text

    Example usage:
        get_weather("San Francisco", "imperial") → "72°F, Partly cloudy"
    """
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return "Error: WEATHER_API_KEY not configured"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": location, "units": units, "appid": api_key},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            unit = "°F" if units == "imperial" else "°C"

            return f"{temp:.1f}{unit}, {desc.capitalize()}"

    except httpx.HTTPError as e:
        return f"Error fetching weather: {str(e)}"
    except KeyError:
        return "Error: Invalid API response format"

# Run server
if __name__ == "__main__":
    mcp.run()
```

### Create TypeScript MCP Server

```typescript
// github-server.ts - Example MCP server using TypeScript SDK
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new Server(
  { name: "github-server", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// Input validation with Zod
const SearchReposInput = z.object({
  query: z.string().describe("Search query (e.g., 'language:python stars:>100')"),
  per_page: z.number().min(1).max(100).default(10).describe("Results per page (1-100)"),
}).strict();

// Tool registration
server.registerTool({
  name: "search_repositories",
  description: "Search GitHub repositories with filters",
  inputSchema: {
    type: "object",
    properties: {
      query: { type: "string", description: "Search query" },
      per_page: { type: "number", description: "Results per page (1-100)" },
    },
    required: ["query"],
  },
  annotations: {
    readOnlyHint: true,
    openWorldHint: true,
  },
}, async (args) => {
  const { query, per_page } = SearchReposInput.parse(args);

  try {
    const response = await fetch(
      `https://api.github.com/search/repositories?q=${encodeURIComponent(query)}&per_page=${per_page}`,
      {
        headers: {
          "Accept": "application/vnd.github.v3+json",
          "User-Agent": "MCP-GitHub-Server",
        },
      }
    );

    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.statusText}`);
    }

    const data = await response.json();
    const repos = data.items.map((repo: any) => ({
      name: repo.full_name,
      stars: repo.stargazers_count,
      url: repo.html_url,
      description: repo.description || "No description",
    }));

    return {
      content: [{ type: "text", text: JSON.stringify(repos, null, 2) }],
    };

  } catch (error) {
    return {
      content: [{ type: "text", text: `Error: ${error.message}` }],
      isError: true,
    };
  }
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

### Build and Test MCP Server

```bash
# Python: Validate syntax
python -m py_compile weather_server.py

# TypeScript: Build
npm run build
# Verifies: dist/index.js created

# Test server with evaluation harness
python skills/mcp-builder/scripts/evaluation.py github-server-eval.xml
```

## Creative Design Skills

### Slack GIF Creator

```python
from core.gif_builder import GIFBuilder
from PIL import Image, ImageDraw

# Create builder for Slack emoji GIF
builder = GIFBuilder(width=128, height=128, fps=10)

# Generate animation frames
for i in range(12):
    frame = Image.new('RGB', (128, 128), (240, 248, 255))
    draw = ImageDraw.Draw(frame)

    # Draw animation elements
    # (circles, polygons, lines, etc.)

    builder.add_frame(frame)

# Save optimized GIF
builder.save('animation.gif', optimize=True, colors=48)
```

**Slack Requirements:**
- Emoji GIFs: 128x128 pixels
- Message GIFs: 480x480 pixels
- FPS: 10-30 (lower = smaller file)
- Colors: 48-128 (fewer = smaller file)
- Duration: Keep under 3 seconds for emojis

### Algorithmic Art with p5.js

```javascript
// Generative art using p5.js with seeded randomness
function setup() {
  createCanvas(800, 800);
  randomSeed(12345);  // Reproducible randomness
  noLoop();
}

function draw() {
  background(240);

  // Flow field particle system
  let particles = [];
  for (let i = 0; i < 1000; i++) {
    particles.push({
      x: random(width),
      y: random(height),
      angle: noise(i * 0.01) * TWO_PI
    });
  }

  // Draw particles following flow field
  for (let p of particles) {
    let x = p.x + cos(p.angle) * 2;
    let y = p.y + sin(p.angle) * 2;
    stroke(0, 50);
    line(p.x, p.y, x, y);
  }
}
```

### Canvas Design

Create visual art in PNG and PDF formats using design philosophies:
- Typography-driven compositions
- Geometric patterns and shapes
- Color theory and palette design
- Layout principles and negative space

### Frontend Design

```typescript
// Create distinctive, production-grade interfaces
// Avoid generic AI aesthetics (Inter font, purple gradients)

// Example: Bold typographic landing page
function LandingPage() {
  return (
    <div className="min-h-screen bg-zinc-900 text-white">
      <header className="p-8">
        <h1 className="text-8xl font-serif tracking-tight">
          Distinctive<br/>Design
        </h1>
      </header>

      <section className="grid grid-cols-2 gap-8 p-8">
        <div className="space-y-4">
          <p className="text-2xl font-light leading-relaxed">
            Production-grade interfaces with intentional aesthetics
          </p>
        </div>
      </section>
    </div>
  );
}
```

**Key Principles:**
- Choose distinctive fonts (avoid Inter, Roboto, Arial)
- Commit to a bold aesthetic direction
- Use animations for micro-interactions
- Create unexpected layouts and compositions

## Enterprise Communication Skills

### Theme Factory

Apply professional themes to any artifact with 10 pre-set options:

1. **Ocean Depths** - Professional maritime theme
2. **Sunset Boulevard** - Warm sunset colors
3. **Forest Canopy** - Natural earth tones
4. **Modern Minimalist** - Clean grayscale
5. **Golden Hour** - Rich autumnal palette
6. **Arctic Frost** - Cool winter theme
7. **Desert Rose** - Soft dusty tones
8. **Tech Innovation** - Bold tech aesthetic
9. **Botanical Garden** - Fresh garden colors
10. **Classic Elegance** - Timeless professional

Each theme includes cohesive color palettes, complementary font pairings, and distinct visual identity.

### Brand Guidelines

Apply Anthropic's official brand colors and typography to artifacts:
- Primary colors and accent palettes
- Typography specifications
- Layout and spacing guidelines
- Logo usage rules

### Internal Communications

Write professional internal communications:
- Status reports and project updates
- Team newsletters and announcements
- FAQs and knowledge base articles
- Policy documents and guidelines

## Skill Creator Workflow

### Complete Skill Creation Process

```bash
# Step 1: Understand requirements (ask user)
# - What functionality should the skill support?
# - Example usage scenarios?
# - What would trigger this skill?

# Step 2: Initialize skill structure
python skills/skill-creator/scripts/init_skill.py bigquery-helper --path ./skills

# Step 3: Develop skill contents
cd skills/bigquery-helper

# Add scripts for common operations
cat > scripts/run_query.py << 'EOF'
#!/usr/bin/env python3
from google.cloud import bigquery
import sys

client = bigquery.Client()
query = sys.argv[1]
df = client.query(query).to_dataframe()
print(df.to_string())
EOF

# Add reference documentation
cat > references/schema.md << 'EOF'
# BigQuery Schema

## users table
- user_id: INT64 (primary key)
- email: STRING
- created_at: TIMESTAMP

## events table
- event_id: INT64 (primary key)
- user_id: INT64 (foreign key → users)
- event_type: STRING
- timestamp: TIMESTAMP
EOF

# Step 4: Edit SKILL.md
# Update frontmatter description and add procedural instructions

# Step 5: Validate and package
cd ../..
python skills/skill-creator/scripts/package_skill.py skills/bigquery-helper ./dist
# Output: dist/bigquery-helper.zip

# Step 6: Iterate based on testing
# Use skill on real tasks, identify improvements, update contents
```

## Skills System Integration

The Claude Skills System enables specialized task performance through structured knowledge delivery. Skills can be created for any domain requiring procedural workflows, tool integration, or standardized outputs. Common patterns include document generation (PDF, XLSX, DOCX, PPTX), collaborative document co-authoring workflows, web automation (Playwright testing), API integration (MCP servers), creative workflows (algorithmic art, canvas design, frontend development), and enterprise processes (brand guidelines, internal communications, themed presentations).

Skills are distributed as zip files and installed via Claude Code's plugin marketplace system. Once registered, Claude automatically loads relevant skills based on task context, user mentions, or file type triggers. The progressive disclosure model ensures optimal context usage while maintaining access to comprehensive domain knowledge through on-demand resource loading. This architecture supports both simple single-file skills and complex multi-component systems with bundled scripts, extensive documentation, and template assets.
