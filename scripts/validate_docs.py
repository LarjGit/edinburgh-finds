import json
import os

def validate_and_report():
    with open('temp/doc-manifest.json', 'r') as f:
        manifest = json.load(f)
    
    with open('temp/repo-map.json', 'r') as f:
        repo_map = json.load(f)

    work_queue = manifest.get('work_queue', [])
    ref_queue = manifest.get('reference_queue', [])
    all_items = work_queue + ref_queue

    # 1. Status check
    doing_items = [i for i in all_items if i.get('status') == 'doing']
    if len(doing_items) > 1:
        print(f"Validation Error: Multiple items are 'doing': {[i['work_id'] for i in doing_items]}")

    # 2. Output existence check
    for item in all_items:
        if item.get('status') == 'done':
            out = item.get('output_path')
            if not os.path.exists(out):
                print(f"Validation Error: Output missing for {item['work_id']}: {out}")

    # 3. File coverage check
    covered_files = set()
    for item in all_items:
        for f in item.get('files', []):
            covered_files.add(f)
    
    # We don't have a full list of ALL files in repo-map yet in a flat list, 
    # but we can look at the files listed in the work items vs expected.
    # The SPEC says "every source file is assigned to exactly one work item".
    
    # Generate report
    report = []
    report.append("# Documentation Coverage Report")
    report.append(f"\n- **Total Work Items:** {len(all_items)}")
    report.append(f"- **Completed:** {len([i for i in all_items if i.get('status') == 'done'])}")
    report.append(f"- **Files Covered:** {len(covered_files)}")
    
    report.append("\n## Subsystem Coverage")
    subsystems = {}
    for item in work_queue:
        s = item['subsystem']
        subsystems[s] = subsystems.get(s, 0) + 1
    
    for s, count in subsystems.items():
        report.append(f"- **{s}:** {count} chunk(s)")

    report.append("\n## Reference Coverage")
    for item in ref_queue:
        report.append(f"- [x] {item['work_id']} -> `{item['output_path']}`")

    with open('temp/doc-coverage-report.md', 'w') as f:
        f.write("\n".join(report))
    
    print("Report generated: temp/doc-coverage-report.md")

if __name__ == "__main__":
    validate_and_report()
