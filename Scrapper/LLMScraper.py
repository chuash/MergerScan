import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def main():
    browser_conf = BrowserConfig(headless=False)  # or False to see the browser
    
    md_generator = DefaultMarkdownGenerator(
    content_filter=PruningContentFilter(threshold=0.4, threshold_type="fixed")
    )
    
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=md_generator
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        result = await crawler.arun(
            url="https://news.ycombinator.com",
            config=run_conf
        )
        with open("markdown.md", "w", encoding="utf-8") as f:
            f.write(result.markdown)
        print("markdown length: ", len(result.markdown))
        print("\n\n")
        with open("raw_markdown.md", "w", encoding="utf-8") as f:
            f.write(result.markdown.raw_markdown)
        print("raw markdown length: ", len(result.markdown.raw_markdown))
        print("\n\n")
        with open("filtered_markdown.md", "w", encoding="utf-8") as f:
            f.write(result.markdown.fit_markdown)
        print("filtered markdown length: ", len(result.markdown.fit_markdown))
        print(type(result), result.url, result.success, result.error_message)
        #print("discovered links: ", result.links)
        #print(result)
       #print("extracted content: ", result.extracted_content)
       # print("crawled urls: ", result.crawled_urls, result.url)
       # print("error messages: ", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
