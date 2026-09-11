-- Keep long exact paths/settings readable in narrow tables without altering source text.
function Code(el)
  if FORMAT:match('latex') and #el.text > 27 and not el.text:match('[{}\\]') and not el.text:match('%s') then
    return pandoc.RawInline('latex', '{\\urlstyle{tt}\\nolinkurl{' .. el.text .. '}}')
  end
end
