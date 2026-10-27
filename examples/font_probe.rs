#[path = "yohaku_workspace/text_font.rs"]
mod text_font;

fn main() {
    for character in "你好👋粘贴abc".chars() {
        let font = text_font::for_character(character);
        let (metrics, bitmap) = font.rasterize(character, 24.0);
        let supported = font.has_glyph(character);
        let visible = bitmap.iter().any(|coverage| *coverage > 0);
        println!("character={character} codepoint=U+{:04X} font={:?} glyph={} visible={} advance={} primary={}",
            character as u32, font.name(), font.lookup_glyph_index(character), visible,
            metrics.advance_width, std::ptr::eq(font, text_font::primary()));
        assert!(supported && visible && metrics.advance_width > 0.0);
        assert_eq!(font.metrics(character, 24.0).advance_width, metrics.advance_width);
    }
}
