# Confluence to BookStack Migration Tool

A Python tool to migrate content from Confluence exports to BookStack, preserving the hierarchical structure and content formatting.

## 🚀 Features

- Preserves Confluence space structure (Shelves → Books → Chapters → Pages)
- Maintains HTML formatting, images, and internal links within the same space
- Detailed migration progress and error reporting

## 📋 Requirements

- Python 3.13+
- Poetry
- BookStack instance with API access
- Confluence HTML export


## 🛠️ Installation

```bash
git clone https://github.com/roxxorarc/Confluence-to-bookstack
cd Confluence-to-bookstack
poetry install
```

## ⚙️ Configuration

This tool can be configured both via environment variables and command line arguments, it prioritizes command line arguments over environment variables.

### Environment Variables

Copy the `.env.example` file to `.env` and fill in your BookStack API details and Confluence export path:

```env
SOURCE_PATH=path/to/confluence/export
BOOKSTACK_URL=https://your-bookstack-instance.com/api
BOOKSTACK_API_ID=your_api_token_id
BOOKSTACK_API_SECRET=your_api_token_secret
```

### CLI Arguments

`.env` configuration can be overridden via command line:
```bash
python main.py -s /path/to/confluence/export \
               -url https://bookstack.com/api \
               -id your_api_id \
               -secret your_api_secret
```
### Other configuration

If you want to display inline PDFs, you need to add a custom code snippet to the `Custom HTML Head Content` section in your BookStack settings.

See [this issue comment](https://github.com/BookStackApp/BookStack/issues/705#issuecomment-1878480380) for an example and further details.

You may also need to increase the `API_REQUESTS_PER_MIN` value in your BookStack instance’s `.env` file to avoid rate limiting errors.  
See: [API Error: Too Many Attempts](https://www.bookstackapp.com/docs/admin/api/#rate-limiting)


## ▶️ Usage

```bash
python main.py
```

## 📊 Migration Mapping

| Confluence | BookStack | 
|------------|-----------|
| Space | Shelf | 
| Pages (Level 1) | Book |
| Pages (Level 2) | Chapter |
| Pages (Level 3+) | Page |

Due to BookStack constraints, it also creates a page for each book and chapter, with the content of the first page in that level.

## 📄 License

MIT License

## 🔗 Related Links

- [BookStack API Reference](https://demo.bookstackapp.com/api/docs)
- [Confluence Export Guide](https://confluence.atlassian.com/doc/export-content-to-word-pdf-html-and-xml-139475.html)