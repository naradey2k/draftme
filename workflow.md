Here’s the detailed workflow after you upload a CV and provide a job description.

  1. User Input
  You start in the Gradio UI with:

  - A PDF resume upload
  - Either a job URL or pasted job description
  - Optional optimizer instructions
  - Local LLM settings:
      - API base URL
      - LLM model
      - Embedding model

  - Run settings:
      - max iterations
      
  The resume input is intentionally limited to PDF only.

  2. PDF Text Extraction
  The app receives the uploaded PDF path and checks that the file extension is .pdf.

  Then it extracts text using PyMuPDF:

  extract_text_from_pdf(resume_path)

  If the extracted text is empty, the run stops with an error.

  At this point, the original PDF is not edited directly. It is only used as the factual source for the new optimized resume.

  3. Job Description Loading
  User pastes job description

  4. Local LLM Configuration
  Before any agent runs, the app applies temporary model settings through settings_override.
  Use Modal deployed models through vLLM

  Listed models: nemotron 30b, minicpm 1b, qwen3.5 (below 32b)
  EMBEDDING_MODEL=openai/nomic-embed-text

  The local LLM is used for the agentic parts:

  - name/language extraction
  - job parsing
  - resume optimization
  - LLM-based validation filters

  The embedding model is used for semantic similarity checks.

  5. Resume Metadata Extraction
  The app sends the extracted resume text to the name extractor agent.

  That agent returns:

  - first name
  - last name
  
  Then the app builds a ResumeSource object containing:

  - raw extracted resume text
  - candidate name
  - original filename
  
  This object becomes the canonical source of truth for the optimization run.

  6. Job Parsing
  The job description is sent to the job parser agent.

  It returns structured job data, usually including:

  - job title
  - company
  - required skills
  - responsibilities
  - keywords
  
  This structured JobPosting object is what the optimizer and filters use later.

  
  8. Optimization Loop Starts
  The core function is:

  optimize_for_job(...)

  Inputs include:

  - ResumeSource
  - parsed JobPosting
  - max iterations
  
  Each iteration follows the same cycle.

  9. Resume Generation
  The optimizer agent receives:

  - original resume text
  - parsed job data
  
  It generates optimized resume HTML.

  Important rules enforced in the prompt:

  - Do not fabricate jobs, companies, degrees, achievements, metrics, or tools.
  - Preserve contact information and links.
  - Prefer job-relevant experience.
  - Add only supported keywords.
  - Fit into one page.
  - Call the length-checking tool before final output.

  The optimizer does not generate a PDF directly. It generates HTML body content.

  10. Internal Tool Calls
  During generation, the optimizer can call tools such as:

  - content length check
  - keyword check
  - structure validation
  - PDF preview rendering

  The most important one is the content length check. It renders the HTML to PDF and checks whether it fits one page.

  If it does not fit, the optimizer is expected to trim and try again before returning.

  11. Render HTML to PDF
  After the optimizer returns HTML, the app renders it with WeasyPrint.

  Then it extracts text back out of the generated PDF.

  This is important because validation checks what an ATS-like system would actually see in the PDF, not just the raw HTML.

  12. Validation Filters
  The generated resume is checked by multiple filters.

  Typical filters include:

  - ContentLengthChecker: checks resume size/page fit
  - DataValidator: validates HTML structure
  - HallucinationChecker: checks whether claims are supported by the original CV
  - KeywordMatcher: compares job keywords against the resume
  - LLMChecker: LLM-based ATS and visual review
  - VectorSimilarityMatcher: semantic similarity between source/job/output
  - AIGeneratedChecker: checks for AI-sounding writing
  - TranslationQualityChecker: checks translation quality when language changes

  If filters run in parallel, the app evaluates them together for speed.

  If filters run sequentially, it can stop early after an important failure.

  13. Iteration Feedback
  After each iteration, the app records:

  - iteration number
  - pass/fail status
  - filter scores
  - filter thresholds
  - validation issues

  If validation fails, that feedback is passed into the next optimizer iteration.

  So the next attempt is not blind. It knows what failed and can adjust the resume.

  Examples:

  - Too long → trim content
  - Missing keywords → include supported keywords from original CV
  - Hallucination risk → remove unsupported claim
  - Poor translation → improve target-language wording
  - Weak ATS match → emphasize more relevant experience

  14. Stop Condition
  The loop stops when either:

  - all validation filters pass, or
  - max iterations is reached

  If the final version still has unresolved checks, the app can still return the generated PDF, but the status says it was generated with unresolved
  checks.

  15. Debug Output
  If debug mode is enabled, each iteration is saved under:

  output/<run_id>_debug_<company>_<role>/

  It can include:

  - iteration_1.html
  - iteration_1.pdf
  - iteration_2.html
  - iteration_2.pdf

  This is useful for inspecting why the optimizer changed something between attempts.

  16. Final PDF Save
  The final PDF is saved under output/.

  The filename is generated from:

  - run timestamp
  - candidate first name
  - candidate last name
  - company
  - job title
  - language code

  Example shape:

  output/0614_1530_jane_doe_acme_ml_engineer_en.pdf

  17. UI Result
  The Gradio UI returns:

  - downloadable optimized PDF
  - summary status
  - candidate name
  - parsed job title/company
  - output language
  - saved file path
  - iteration details

  So the user ends with a new tailored PDF resume generated from the uploaded CV and the provided job description.