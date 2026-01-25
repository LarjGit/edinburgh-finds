import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# --- Configuration ---
REPO_ROOT = os.getcwd()
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

EXCLUDE_DIRS = {
    '.git', 'node_modules', 'archive', 'docs', 'temp', 'dist', 'build', 'out',
    '.next', '.turbo', '.cache', '.parcel-cache', '__pycache__', '.pytest_cache',
    '.venv', 'venv', 'env', 'htmlcov', '.vscode', '.idea', '.obsidian', '.claude',
    '.doc-suite', '.prune-suite'
}

EXCLUDE_PATTERNS = {'.map', '.chunk.js', '.min.js', '.pyc'}

MAX_FILES_PER_STEP = 20
MAX_LOC_PER_STEP = 2000

# --- Helper Functions ---

def normalize_path(path):
    """Convert backslashes to forward slashes."""
    return str(path).replace('\\', '/')

def setup_directories():
    """Backup docs and reset temp."""
    print(f"Setting up directories in {REPO_ROOT}...")
    
    docs_path = Path("docs")
    archive_dir = Path(f"archive/docs_backup_{TIMESTAMP}")
    
    if docs_path.exists():
        if not archive_dir.parent.exists():
            archive_dir.parent.mkdir(parents=True)
        print(f"Backing up docs/ to {archive_dir}...")
        shutil.move(str(docs_path), str(archive_dir))
    
    # Create fresh docs structure
    os.makedirs("docs/architecture/subsystems", exist_ok=True)
    os.makedirs("docs/reference", exist_ok=True)
    os.makedirs("docs/howto", exist_ok=True)
    os.makedirs("docs/operations", exist_ok=True)
    
    # Reset temp
    temp_path = Path("temp")
    if not temp_path.exists():
        temp_path.mkdir()
    
    for f in ["doc-manifest.json", "repo-map.json", "doc-coverage-report.md"]:
        p = temp_path / f
        if p.exists():
            p.unlink()

def detect_subsystem(path_str):
    """
    Assign subsystem based on path patterns.
    path_str is relative to root and normalized (forward slashes).
    """
    parts = path_str.split('/')
    ext = Path(path_str).suffix.lower()
    name = Path(path_str).name.lower()
    
    # 1. Frontend/UI
    # Patterns: src/app/**, src/pages/**, src/components/**, app/**, pages/**, components/**
    # Extensions: .tsx, .jsx, .vue, .svelte
    frontend_triggers = {'app', 'pages', 'components', 'web'} # Added 'web' as likely container
    if any(p in parts for p in frontend_triggers) and ext in {'.tsx', '.jsx', '.vue', '.svelte', '.css', '.scss'}:
        return 'frontend'
    if parts[0] == 'web': # Specific override for this project structure if it contains frontend code
         if ext in {'.tsx', '.jsx', '.ts', '.js', '.json', '.css'}:
             return 'frontend'

    # 2. Backend/API
    # Patterns: src/api/**, api/**, server/**, backend/**, routes/**, controllers/**
    backend_triggers = {'api', 'server', 'backend', 'routes', 'controllers'}
    if any(p in parts for p in backend_triggers) and ext in {'.py', '.ts', '.js', '.go', '.java'}:
        return 'backend'

    # 3. Database/Schema
    # Patterns: prisma/**, migrations/**, alembic/**, src/db/**, database/**, models/**, schema/**
    # Files: schema.prisma, *.sql
    db_triggers = {'prisma', 'migrations', 'alembic', 'db', 'database', 'models', 'schema'}
    if (any(p in parts for p in db_triggers) or name == 'schema.prisma' or ext == '.sql'):
        return 'database'

    # 4. Core Business Logic
    # Patterns: src/lib/**, lib/**, src/core/**, core/**, src/engine/**, engine/**, domain/**
    core_triggers = {'lib', 'core', 'engine', 'domain'}
    for trigger in core_triggers:
        if trigger in parts:
            return trigger # Return the specific name (e.g., 'engine')
            
    # 5. Testing
    # Patterns: tests/**, test/**, __tests__/**, **/*.test.*, **/*.spec.*
    if 'tests' in parts or 'test' in parts or '__tests__' in parts or '.test.' in name or '.spec.' in name or name.startswith('test_'):
        return 'tests'

    # 6. Scripts & Automation
    # Patterns: scripts/**, tools/**, bin/**
    # Extensions: .sh, .bash, .py (in scripts contexts)
    script_triggers = {'scripts', 'tools', 'bin'}
    if any(p in parts for p in script_triggers) or ext in {'.sh', '.bash', '.ps1', '.bat'}:
        return 'scripts'

    # 7. Infrastructure & CI/CD
    # Patterns: .github/workflows/**, docker/**, k8s/**, terraform/**, .gitlab-ci.yml
    # Files: Dockerfile, docker-compose*.yml, *.tf
    infra_dirs = {'.github', 'docker', 'k8s', 'terraform'}
    if any(p in parts for p in infra_dirs) or name.startswith('dockerfile') or name.startswith('docker-compose') or ext == '.tf':
        return 'infrastructure'

    # 8. Configuration
    # Root-level files only
    if len(parts) == 1 and ext in {'.json', '.yml', '.yaml', '.toml', '.env', '.ini', '.cfg'} or name in {'package.json', 'tsconfig.json', 'pyproject.toml', 'requirements.txt', 'poetry.lock'}:
        return 'config'
    # Config files in root of major dirs (like web/package.json)
    if name in {'package.json', 'tsconfig.json', 'pyproject.toml', 'requirements.txt'}:
        return 'config'

    # 9. Documentation Source
    if name.startswith('readme') or name.startswith('contributing') or name.startswith('license') or (len(parts) == 1 and ext == '.md'):
        return 'docs-source'

    # 10. Fallback
    if len(parts) > 1:
        return parts[0]
    
    return 'root'

def detect_kind(path_str):
    ext = Path(path_str).suffix.lower()
    name = Path(path_str).name.lower()
    
    source_exts = {'.py', '.ts', '.tsx', '.js', '.jsx', '.vue', '.svelte', '.go', '.java', '.c', '.cpp', '.h'}
    config_exts = {'.json', '.yml', '.yaml', '.toml', '.env', '.ini'}
    script_exts = {'.sh', '.bash', '.ps1', '.bat'}
    
    if ext in source_exts:
        return 'source'
    elif ext in config_exts or name.endswith('rc'):
        return 'config'
    elif ext in script_exts:
        return 'script'
    elif ext == '.md' or ext == '.txt':
        return 'doc'
    return 'other'

def count_lines(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except:
        return 0

def get_git_commit():
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except:
        return None

def scan_repository():
    print("Scanning repository...")
    files = []
    
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        # Apply excludes in-place
        dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDE_DIRS]
        
        for filename in filenames:
            # Check pattern excludes
            if any(filename.lower().endswith(ext) for ext in EXCLUDE_PATTERNS):
                continue
                
            full_path = Path(dirpath) / filename
            rel_path = full_path.relative_to(REPO_ROOT)
            norm_path = normalize_path(rel_path)
            
            subsystem = detect_subsystem(norm_path)
            
            # Additional filter: Exclude 'generated' files logic could go here if needed
            
            file_info = {
                'path': norm_path,
                'subsystem': subsystem,
                'kind': detect_kind(norm_path),
                'loc': count_lines(full_path),
                'extension': full_path.suffix
            }
            files.append(file_info)
            
    return sorted(files, key=lambda f: f['path'])

def build_manifest(files):
    from collections import defaultdict
    
    subsystem_files = defaultdict(list)
    for f in files:
        subsystem_files[f['subsystem']].append(f)
        
    work_queue = []
    
    # Priority sorting
    priority_order = {'infrastructure': 0, 'scripts': 1, 'config': 2, 'backend': 3, 'engine': 4, 'core': 4, 'frontend': 5, 'tests': 6}
    
    def get_priority(sub_name):
        return priority_order.get(sub_name, 100) # Default low priority
        
    sorted_subsystems = sorted(subsystem_files.keys(), key=lambda s: (get_priority(s), s))
    
    for subsystem in sorted_subsystems:
        sub_files = subsystem_files[subsystem]
        file_count = len(sub_files)
        total_loc = sum(f['loc'] for f in sub_files)
        
        if file_count <= MAX_FILES_PER_STEP:
            work_queue.append({
                'id': subsystem,
                'subsystem': subsystem,
                'files': [f['path'] for f in sub_files],
                'file_count': file_count,
                'total_loc': total_loc,
                'output_path': f'docs/architecture/subsystems/{subsystem}.md',
                'status': 'todo'
            })
        else:
            # Split logic
            for i in range(0, file_count, MAX_FILES_PER_STEP):
                part_files = sub_files[i:i+MAX_FILES_PER_STEP]
                part_num = (i // MAX_FILES_PER_STEP) + 1
                
                work_queue.append({
                    'id': f'{subsystem}-part{part_num}',
                    'subsystem': subsystem,
                    'files': [f['path'] for f in part_files],
                    'file_count': len(part_files),
                    'total_loc': sum(f['loc'] for f in part_files),
                    'output_path': f'docs/architecture/subsystems/{subsystem}.md',
                    'status': 'todo'
                })
                
    return work_queue, subsystem_files

def main():
    print(f"DOC-SUITE: INIT - Started at {TIMESTAMP}")
    
    setup_directories()
    
    files = scan_repository()
    work_queue, subsystem_map = build_manifest(files)
    
    # Build repo-map.json
    repo_map = {
        "repo_root": normalize_path(REPO_ROOT),
        "excludes": {
            "directories": list(EXCLUDE_DIRS),
            "patterns": list(EXCLUDE_PATTERNS)
        },
        "limits": {
            "max_files_per_step": MAX_FILES_PER_STEP,
            "max_loc_per_step": MAX_LOC_PER_STEP
        },
        "files": files,
        "subsystems": {
            name: {
                "file_count": len(subs),
                "total_loc": sum(f['loc'] for f in subs),
                "primary_extensions": list(set(f['extension'] for f in subs))
            } for name, subs in subsystem_map.items()
        }
    }
    
    with open("temp/repo-map.json", "w") as f:
        json.dump(repo_map, f, indent=2)
        
    # Build doc-manifest.json
    manifest = {
        "version": "1.0",
        "limits": {
            "max_files_per_step": MAX_FILES_PER_STEP,
            "max_loc_per_step": MAX_LOC_PER_STEP
        },
        "excludes": repo_map["excludes"],
        "baseline": {
            "timestamp": datetime.now().isoformat(),
            "commit": get_git_commit()
        },
        "work_queue": work_queue,
        "outputs": []
    }
    
    with open("temp/doc-manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    # Summary
    print("\nDOC-SUITE: INIT Complete")
    print(f"- Repository root: {REPO_ROOT}")
    print(f"- Files scanned: {len(files)}")
    print(f"- Subsystems identified: {len(subsystem_map)}")
    print(f"- Work items created: {len(work_queue)}")
    print(f"- State files: temp/repo-map.json, temp/doc-manifest.json")
    print("- Ready for: DOC-SUITE: STEP")

if __name__ == "__main__":
    main()
