"""
Report generation functionality for batch processing results.
"""

import os
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, List, Any

class BatchReport:
    """Generate detailed reports for batch processing operations."""

    def __init__(self, dest_path: Path):
        self.dest_path = dest_path
        self.timestamp = datetime.now()
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "skipped_files": 0,
            "error_files": 0,
            "total_size": 0,
            "years": {},
            "formats": {},
            "errors": []
        }
        self.source_folders: List[Dict[str, Any]] = []

    def add_source_folder(self, folder: Path, files: int, size: int, duration: float):
        """Add statistics for a processed source folder."""
        self.source_folders.append({
            "path": str(folder),
            "files": files,
            "size": size,
            "duration": duration,
            "status": "completed"
        })

    def add_error(self, folder: Path, error: str):
        """Add an error that occurred during processing."""
        self.stats["errors"].append({
            "folder": str(folder),
            "error": str(error),
            "timestamp": datetime.now().isoformat()
        })

    def update_stats(self, file_stats: Dict[str, Any]):
        """Update overall statistics with information from a processed file."""
        self.stats["total_files"] += 1
        self.stats["total_size"] += file_stats.get("size", 0)

        # Update year statistics
        year = file_stats.get("year")
        if year:
            self.stats["years"][year] = self.stats["years"].get(year, 0) + 1

        # Update format statistics
        fmt = file_stats.get("format")
        if fmt:
            self.stats["formats"][fmt] = self.stats["formats"].get(fmt, 0) + 1

        # Update processing status
        if file_stats.get("status") == "processed":
            self.stats["processed_files"] += 1
        elif file_stats.get("status") == "skipped":
            self.stats["skipped_files"] += 1
        elif file_stats.get("status") == "error":
            self.stats["error_files"] += 1

    def generate_html_report(self) -> Path:
        """Generate an HTML report with processing statistics and charts."""
        report_dir = self.dest_path / "reports"
        report_dir.mkdir(exist_ok=True)

        timestamp_str = self.timestamp.strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"batch_report_{timestamp_str}.html"

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Music Organization Report</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .stat-card {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #2196F3;
                }}
                .chart-container {{
                    margin-bottom: 30px;
                }}
                .error-list {{
                    background: #fff3f3;
                    padding: 15px;
                    border-radius: 6px;
                    margin-top: 20px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background: #f8f9fa;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Music Organization Report</h1>
                <p>Generated on {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>

            <div class="container">
                <h2>Processing Summary</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total Files</h3>
                        <div class="stat-value">{self.stats["total_files"]}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Processed</h3>
                        <div class="stat-value">{self.stats["processed_files"]}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Skipped</h3>
                        <div class="stat-value">{self.stats["skipped_files"]}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Errors</h3>
                        <div class="stat-value">{self.stats["error_files"]}</div>
                    </div>
                </div>

                <div class="chart-container">
                    <h2>Files by Year</h2>
                    <canvas id="yearChart"></canvas>
                </div>

                <div class="chart-container">
                    <h2>Files by Format</h2>
                    <canvas id="formatChart"></canvas>
                </div>

                <h2>Processed Folders</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Folder</th>
                            <th>Files</th>
                            <th>Size</th>
                            <th>Duration</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(f'''
                        <tr>
                            <td>{folder["path"]}</td>
                            <td>{folder["files"]}</td>
                            <td>{self._format_size(folder["size"])}</td>
                            <td>{self._format_duration(folder["duration"])}</td>
                            <td>{folder["status"]}</td>
                        </tr>
                        ''' for folder in self.source_folders)}
                    </tbody>
                </table>

                {self._generate_error_section()}
            </div>

            <script>
                // Year distribution chart
                new Chart(document.getElementById('yearChart'), {{
                    type: 'bar',
                    data: {{
                        labels: {list(self.stats["years"].keys())},
                        datasets: [{{
                            label: 'Files per Year',
                            data: {list(self.stats["years"].values())},
                            backgroundColor: '#2196F3'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true
                            }}
                        }}
                    }}
                }});

                // Format distribution chart
                new Chart(document.getElementById('formatChart'), {{
                    type: 'pie',
                    data: {{
                        labels: {list(self.stats["formats"].keys())},
                        datasets: [{{
                            data: {list(self.stats["formats"].values())},
                            backgroundColor: [
                                '#2196F3',
                                '#4CAF50',
                                '#FFC107',
                                '#F44336',
                                '#9C27B0',
                                '#00BCD4'
                            ]
                        }}]
                    }},
                    options: {{
                        responsive: true
                    }}
                }});
            </script>
        </body>
        </html>
        """

        report_file.write_text(html_content)
        return report_file

    def generate_json_report(self) -> Path:
        """Generate a JSON report with all statistics."""
        report_dir = self.dest_path / "reports"
        report_dir.mkdir(exist_ok=True)

        timestamp_str = self.timestamp.strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"batch_report_{timestamp_str}.json"

        report_data = {
            "timestamp": self.timestamp.isoformat(),
            "destination": str(self.dest_path),
            "statistics": self.stats,
            "source_folders": self.source_folders
        }

        report_file.write_text(json.dumps(report_data, indent=4))
        return report_file

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        minutes = int(seconds / 60)
        hours = int(minutes / 60)
        if hours > 0:
            return f"{hours}h {minutes % 60}m"
        return f"{minutes}m {int(seconds % 60)}s"

    def _generate_error_section(self) -> str:
        """Generate HTML for the error section if there are any errors."""
        if not self.stats["errors"]:
            return ""

        error_html = """
        <div class="error-list">
            <h2>Processing Errors</h2>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Folder</th>
                        <th>Error</th>
                    </tr>
                </thead>
                <tbody>
        """

        for error in self.stats["errors"]:
            error_html += f"""
                <tr>
                    <td>{datetime.fromisoformat(error["timestamp"]).strftime("%H:%M:%S")}</td>
                    <td>{error["folder"]}</td>
                    <td>{error["error"]}</td>
                </tr>
            """

        error_html += """
                </tbody>
            </table>
        </div>
        """

        return error_html
