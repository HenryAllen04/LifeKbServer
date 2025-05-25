# LifeKB iOS UX Implementation Guide

## 🎨 SwiftUI Components & Design System

### Design Tokens

```swift
import SwiftUI

struct LifeKBDesign {
    
    // MARK: - Colors
    struct Colors {
        static let primary = Color("Primary") // Define in Assets.xcassets
        static let secondary = Color("Secondary")
        static let accent = Color("Accent")
        
        static let background = Color("Background")
        static let surface = Color("Surface")
        static let surfaceVariant = Color("SurfaceVariant")
        
        static let textPrimary = Color("TextPrimary")
        static let textSecondary = Color("TextSecondary")
        static let textMuted = Color("TextMuted")
        
        static let success = Color("Success")
        static let warning = Color("Warning")
        static let error = Color("Error")
        
        static let ragConversational = Color("RAGConversational")
        static let ragSummary = Color("RAGSummary")
        static let ragAnalysis = Color("RAGAnalysis")
    }
    
    // MARK: - Typography
    struct Typography {
        static let largeTitle = Font.largeTitle.weight(.bold)
        static let title = Font.title.weight(.semibold)
        static let title2 = Font.title2.weight(.medium)
        static let headline = Font.headline.weight(.medium)
        static let body = Font.body
        static let callout = Font.callout
        static let caption = Font.caption
        static let caption2 = Font.caption2
    }
    
    // MARK: - Spacing
    struct Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
        static let xxl: CGFloat = 48
    }
    
    // MARK: - Corner Radius
    struct CornerRadius {
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 24
    }
}
```

### Reusable UI Components

```swift
// MARK: - Custom Button Styles

struct PrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundColor(.white)
            .font(LifeKBDesign.Typography.headline)
            .padding(.horizontal, LifeKBDesign.Spacing.lg)
            .padding(.vertical, LifeKBDesign.Spacing.md)
            .background(LifeKBDesign.Colors.primary)
            .cornerRadius(LifeKBDesign.CornerRadius.md)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

struct SecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundColor(LifeKBDesign.Colors.primary)
            .font(LifeKBDesign.Typography.headline)
            .padding(.horizontal, LifeKBDesign.Spacing.lg)
            .padding(.vertical, LifeKBDesign.Spacing.md)
            .background(LifeKBDesign.Colors.surface)
            .overlay(
                RoundedRectangle(cornerRadius: LifeKBDesign.CornerRadius.md)
                    .stroke(LifeKBDesign.Colors.primary, lineWidth: 1)
            )
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

// MARK: - Custom Text Field

struct LifeKBTextField: View {
    let title: String
    @Binding var text: String
    let placeholder: String
    var isSecure: Bool = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: LifeKBDesign.Spacing.xs) {
            Text(title)
                .font(LifeKBDesign.Typography.callout)
                .foregroundColor(LifeKBDesign.Colors.textSecondary)
            
            Group {
                if isSecure {
                    SecureField(placeholder, text: $text)
                } else {
                    TextField(placeholder, text: $text)
                }
            }
            .font(LifeKBDesign.Typography.body)
            .padding(LifeKBDesign.Spacing.md)
            .background(LifeKBDesign.Colors.surface)
            .cornerRadius(LifeKBDesign.CornerRadius.sm)
            .overlay(
                RoundedRectangle(cornerRadius: LifeKBDesign.CornerRadius.sm)
                    .stroke(LifeKBDesign.Colors.surfaceVariant, lineWidth: 1)
            )
        }
    }
}

// MARK: - Entry Card Component

struct EntryCard: View {
    let entry: JournalEntry
    let onTap: () -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: LifeKBDesign.Spacing.sm) {
            HStack {
                VStack(alignment: .leading, spacing: LifeKBDesign.Spacing.xs) {
                    Text(entry.createdAt, style: .date)
                        .font(LifeKBDesign.Typography.caption)
                        .foregroundColor(LifeKBDesign.Colors.textSecondary)
                    
                    if !entry.tagsArray.isEmpty {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: LifeKBDesign.Spacing.xs) {
                                ForEach(entry.tagsArray, id: \.self) { tag in
                                    TagChip(text: tag)
                                }
                            }
                            .padding(.horizontal, 1) // Prevent clipping
                        }
                    }
                }
                
                Spacer()
                
                if entry.isEmbedded {
                    Image(systemName: "brain.head.profile")
                        .foregroundColor(LifeKBDesign.Colors.accent)
                        .accessibilityLabel("AI-ready")
                }
                
                if entry.needsSync {
                    Image(systemName: "icloud.and.arrow.up")
                        .foregroundColor(LifeKBDesign.Colors.warning)
                        .accessibilityLabel("Sync pending")
                }
            }
            
            Text(entry.text)
                .font(LifeKBDesign.Typography.body)
                .foregroundColor(LifeKBDesign.Colors.textPrimary)
                .lineLimit(3)
                .multilineTextAlignment(.leading)
        }
        .padding(LifeKBDesign.Spacing.md)
        .background(LifeKBDesign.Colors.surface)
        .cornerRadius(LifeKBDesign.CornerRadius.md)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
        .onTapGesture(perform: onTap)
    }
}

// MARK: - Tag Chip

struct TagChip: View {
    let text: String
    
    var body: some View {
        Text(text)
            .font(LifeKBDesign.Typography.caption2)
            .foregroundColor(LifeKBDesign.Colors.textSecondary)
            .padding(.horizontal, LifeKBDesign.Spacing.sm)
            .padding(.vertical, LifeKBDesign.Spacing.xs)
            .background(LifeKBDesign.Colors.surfaceVariant)
            .cornerRadius(LifeKBDesign.CornerRadius.sm)
    }
}

// MARK: - Loading State

struct LoadingView: View {
    let message: String
    
    var body: some View {
        VStack(spacing: LifeKBDesign.Spacing.md) {
            ProgressView()
                .scaleEffect(1.2)
            
            Text(message)
                .font(LifeKBDesign.Typography.callout)
                .foregroundColor(LifeKBDesign.Colors.textSecondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(LifeKBDesign.Colors.background)
    }
}

// MARK: - Empty State

struct EmptyStateView: View {
    let icon: String
    let title: String
    let message: String
    let actionTitle: String?
    let action: (() -> Void)?
    
    var body: some View {
        VStack(spacing: LifeKBDesign.Spacing.lg) {
            Image(systemName: icon)
                .font(.system(size: 48))
                .foregroundColor(LifeKBDesign.Colors.textMuted)
            
            VStack(spacing: LifeKBDesign.Spacing.sm) {
                Text(title)
                    .font(LifeKBDesign.Typography.title2)
                    .foregroundColor(LifeKBDesign.Colors.textPrimary)
                
                Text(message)
                    .font(LifeKBDesign.Typography.body)
                    .foregroundColor(LifeKBDesign.Colors.textSecondary)
                    .multilineTextAlignment(.center)
            }
            
            if let actionTitle = actionTitle, let action = action {
                Button(actionTitle, action: action)
                    .buttonStyle(PrimaryButtonStyle())
            }
        }
        .padding(LifeKBDesign.Spacing.xl)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(LifeKBDesign.Colors.background)
    }
}
```

## 🔍 Search & RAG Interface

### Search Bar Component

```swift
struct SearchBar: View {
    @Binding var text: String
    @Binding var isSearching: Bool
    let onSearchSubmit: () -> Void
    
    var body: some View {
        HStack {
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(LifeKBDesign.Colors.textSecondary)
                
                TextField("Search your thoughts...", text: $text)
                    .onSubmit(onSearchSubmit)
                
                if !text.isEmpty {
                    Button(action: { text = "" }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(LifeKBDesign.Colors.textSecondary)
                    }
                }
            }
            .padding(LifeKBDesign.Spacing.md)
            .background(LifeKBDesign.Colors.surface)
            .cornerRadius(LifeKBDesign.CornerRadius.md)
            
            if isSearching {
                Button("Cancel") {
                    text = ""
                    isSearching = false
                }
                .foregroundColor(LifeKBDesign.Colors.primary)
                .transition(.move(edge: .trailing))
            }
        }
        .animation(.easeInOut(duration: 0.2), value: isSearching)
    }
}

// MARK: - RAG Mode Selector

struct RAGModeSelector: View {
    @Binding var selectedMode: RAGMode
    
    var body: some View {
        HStack(spacing: LifeKBDesign.Spacing.sm) {
            ForEach(RAGMode.allCases, id: \.self) { mode in
                RAGModeChip(
                    mode: mode,
                    isSelected: selectedMode == mode
                ) {
                    selectedMode = mode
                }
            }
        }
    }
}

struct RAGModeChip: View {
    let mode: RAGMode
    let isSelected: Bool
    let onTap: () -> Void
    
    var body: some View {
        VStack(spacing: LifeKBDesign.Spacing.xs) {
            Image(systemName: mode.icon)
                .font(.system(size: 20))
                .foregroundColor(isSelected ? .white : mode.color)
            
            Text(mode.title)
                .font(LifeKBDesign.Typography.caption)
                .foregroundColor(isSelected ? .white : LifeKBDesign.Colors.textPrimary)
        }
        .padding(.vertical, LifeKBDesign.Spacing.sm)
        .padding(.horizontal, LifeKBDesign.Spacing.md)
        .background(isSelected ? mode.color : LifeKBDesign.Colors.surface)
        .cornerRadius(LifeKBDesign.CornerRadius.md)
        .shadow(color: .black.opacity(0.05), radius: 1, x: 0, y: 1)
        .onTapGesture(perform: onTap)
        .animation(.easeInOut(duration: 0.2), value: isSelected)
    }
}

enum RAGMode: CaseIterable {
    case conversational, summary, analysis
    
    var title: String {
        switch self {
        case .conversational: return "Chat"
        case .summary: return "Summary"
        case .analysis: return "Analysis"
        }
    }
    
    var icon: String {
        switch self {
        case .conversational: return "bubble.left.and.bubble.right"
        case .summary: return "list.bullet.clipboard"
        case .analysis: return "chart.line.uptrend.xyaxis"
        }
    }
    
    var color: Color {
        switch self {
        case .conversational: return LifeKBDesign.Colors.ragConversational
        case .summary: return LifeKBDesign.Colors.ragSummary
        case .analysis: return LifeKBDesign.Colors.ragAnalysis
        }
    }
}

// MARK: - RAG Response View

struct RAGResponseView: View {
    let response: RAGResponse
    
    var body: some View {
        VStack(alignment: .leading, spacing: LifeKBDesign.Spacing.md) {
            // AI Response
            VStack(alignment: .leading, spacing: LifeKBDesign.Spacing.sm) {
                HStack {
                    Image(systemName: "brain.head.profile")
                        .foregroundColor(LifeKBDesign.Colors.accent)
                    
                    Text("AI Insight")
                        .font(LifeKBDesign.Typography.headline)
                        .foregroundColor(LifeKBDesign.Colors.textPrimary)
                    
                    Spacer()
                    
                    Text("\(response.processingTimeMs)ms")
                        .font(LifeKBDesign.Typography.caption2)
                        .foregroundColor(LifeKBDesign.Colors.textMuted)
                }
                
                Text(response.aiResponse)
                    .font(LifeKBDesign.Typography.body)
                    .foregroundColor(LifeKBDesign.Colors.textPrimary)
                    .textSelection(.enabled)
            }
            .padding(LifeKBDesign.Spacing.md)
            .background(LifeKBDesign.Colors.surface)
            .cornerRadius(LifeKBDesign.CornerRadius.md)
            
            // Sources
            if !response.sources.isEmpty {
                VStack(alignment: .leading, spacing: LifeKBDesign.Spacing.sm) {
                    Text("Sources")
                        .font(LifeKBDesign.Typography.headline)
                        .foregroundColor(LifeKBDesign.Colors.textPrimary)
                    
                    ForEach(response.sources.indices, id: \.self) { index in
                        SourceCard(source: response.sources[index], index: index + 1)
                    }
                }
            }
        }
    }
}

struct SourceCard: View {
    let source: RAGSource
    let index: Int
    
    var body: some View {
        VStack(alignment: .leading, spacing: LifeKBDesign.Spacing.xs) {
            HStack {
                Text("Source \(index)")
                    .font(LifeKBDesign.Typography.caption)
                    .foregroundColor(LifeKBDesign.Colors.textSecondary)
                
                Spacer()
                
                Text("\(Int(source.similarity * 100))% match")
                    .font(LifeKBDesign.Typography.caption2)
                    .foregroundColor(LifeKBDesign.Colors.textMuted)
            }
            
            Text(source.text)
                .font(LifeKBDesign.Typography.callout)
                .foregroundColor(LifeKBDesign.Colors.textPrimary)
                .lineLimit(3)
        }
        .padding(LifeKBDesign.Spacing.sm)
        .background(LifeKBDesign.Colors.surfaceVariant)
        .cornerRadius(LifeKBDesign.CornerRadius.sm)
    }
}
```

## ♿ Accessibility Implementation

### Accessibility Helpers

```swift
struct AccessibilityHelper {
    
    // MARK: - VoiceOver Labels
    
    static func entryCardLabel(for entry: JournalEntry) -> String {
        var label = "Journal entry from \(entry.createdAt.formatted(date: .abbreviated, time: .omitted)). "
        label += entry.text
        
        if !entry.tagsArray.isEmpty {
            label += ". Tags: \(entry.tagsArray.joined(separator: ", "))"
        }
        
        if entry.isEmbedded {
            label += ". AI-ready"
        }
        
        if entry.needsSync {
            label += ". Sync pending"
        }
        
        return label
    }
    
    static func ragResponseLabel(for response: RAGResponse) -> String {
        var label = "AI generated insight. "
        label += response.aiResponse
        
        if !response.sources.isEmpty {
            label += ". Based on \(response.sources.count) journal entries."
        }
        
        return label
    }
    
    // MARK: - Dynamic Type Support
    
    static func scaledFont(_ font: Font, maxSizeCategory: ContentSizeCategory = .accessibilityExtraExtraExtraLarge) -> Font {
        return font
    }
    
    // MARK: - Haptic Feedback
    
    static func selectionFeedback() {
        let impactFeedback = UIImpactFeedbackGenerator(style: .light)
        impactFeedback.impactOccurred()
    }
    
    static func successFeedback() {
        let notificationFeedback = UINotificationFeedbackGenerator()
        notificationFeedback.notificationOccurred(.success)
    }
    
    static func errorFeedback() {
        let notificationFeedback = UINotificationFeedbackGenerator()
        notificationFeedback.notificationOccurred(.error)
    }
}

// MARK: - Accessibility Extensions

extension View {
    func accessibleEntryCard(_ entry: JournalEntry) -> some View {
        self
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(AccessibilityHelper.entryCardLabel(for: entry))
            .accessibilityAddTraits(.isButton)
            .accessibilityHint("Double tap to view or edit this entry")
    }
    
    func accessibleRAGResponse(_ response: RAGResponse) -> some View {
        self
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(AccessibilityHelper.ragResponseLabel(for: response))
            .accessibilityAddTraits(.isStaticText)
    }
    
    func hapticFeedback(on trigger: some Equatable, style: UIImpactFeedbackGenerator.FeedbackStyle = .light) -> some View {
        self.onChange(of: trigger) { _ in
            let impactFeedback = UIImpactFeedbackGenerator(style: style)
            impactFeedback.impactOccurred()
        }
    }
}
```

## 📱 Responsive Design & Adaptivity

### Adaptive Layout Helpers

```swift
struct AdaptiveLayout {
    
    // MARK: - Screen Size Detection
    
    static var isCompact: Bool {
        UIScreen.main.bounds.width < 768
    }
    
    static var isRegular: Bool {
        UIScreen.main.bounds.width >= 768
    }
    
    static var columnCount: Int {
        isCompact ? 1 : 2
    }
    
    static var cardSpacing: CGFloat {
        isCompact ? LifeKBDesign.Spacing.md : LifeKBDesign.Spacing.lg
    }
    
    // MARK: - Orientation Helpers
    
    static var isLandscape: Bool {
        UIDevice.current.orientation.isLandscape
    }
    
    static var isPortrait: Bool {
        UIDevice.current.orientation.isPortrait || UIDevice.current.orientation == .unknown
    }
}

// MARK: - Adaptive Grid

struct AdaptiveEntryGrid<Content: View>: View {
    let entries: [JournalEntry]
    @ViewBuilder let content: (JournalEntry) -> Content
    
    private let columns: [GridItem] = Array(
        repeating: GridItem(.flexible(), spacing: AdaptiveLayout.cardSpacing),
        count: AdaptiveLayout.columnCount
    )
    
    var body: some View {
        LazyVGrid(columns: columns, spacing: AdaptiveLayout.cardSpacing) {
            ForEach(entries) { entry in
                content(entry)
            }
        }
    }
}

// MARK: - Safe Area Aware Padding

extension View {
    func adaptivePadding() -> some View {
        self.padding(.horizontal, AdaptiveLayout.isCompact ? LifeKBDesign.Spacing.md : LifeKBDesign.Spacing.xl)
    }
    
    func safeAreaPadding() -> some View {
        self.padding(.horizontal, LifeKBDesign.Spacing.md)
    }
}
```

## 🎭 Animation & Transitions

### Custom Animations

```swift
struct AnimationHelpers {
    
    // MARK: - Standard Animations
    
    static let springAnimation = Animation.spring(response: 0.5, dampingFraction: 0.8)
    static let easeInOut = Animation.easeInOut(duration: 0.3)
    static let quickSpring = Animation.spring(response: 0.3, dampingFraction: 0.7)
    
    // MARK: - Custom Transitions
    
    static var slideUpTransition: AnyTransition {
        AnyTransition.asymmetric(
            insertion: .move(edge: .bottom).combined(with: .opacity),
            removal: .move(edge: .bottom).combined(with: .opacity)
        )
    }
    
    static var scaleTransition: AnyTransition {
        AnyTransition.scale.combined(with: .opacity)
    }
}

// MARK: - Animated Button

struct AnimatedButton<Label: View>: View {
    let action: () -> Void
    @ViewBuilder let label: () -> Label
    
    @State private var isPressed = false
    
    var body: some View {
        Button(action: action) {
            label()
        }
        .scaleEffect(isPressed ? 0.95 : 1.0)
        .animation(AnimationHelpers.quickSpring, value: isPressed)
        .onLongPressGesture(minimumDuration: 0, maximumDistance: .infinity) { _ in
            // Do nothing on press
        } onPressingChanged: { pressing in
            isPressed = pressing
        }
    }
}

// MARK: - Loading Skeleton

struct SkeletonView: View {
    @State private var animationOffset: CGFloat = -1
    
    var body: some View {
        GeometryReader { geometry in
            RoundedRectangle(cornerRadius: LifeKBDesign.CornerRadius.sm)
                .fill(LifeKBDesign.Colors.surfaceVariant)
                .overlay(
                    RoundedRectangle(cornerRadius: LifeKBDesign.CornerRadius.sm)
                        .fill(
                            LinearGradient(
                                colors: [
                                    Color.clear,
                                    Color.white.opacity(0.3),
                                    Color.clear
                                ],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .offset(x: animationOffset * geometry.size.width)
                        .clipped()
                )
        }
        .onAppear {
            withAnimation(
                Animation.linear(duration: 1.5)
                    .repeatForever(autoreverses: false)
            ) {
                animationOffset = 1
            }
        }
    }
}

// MARK: - Expandable Text

struct ExpandableText: View {
    let text: String
    let lineLimit: Int
    
    @State private var isExpanded = false
    @State private var isTruncated = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: LifeKBDesign.Spacing.xs) {
            Text(text)
                .font(LifeKBDesign.Typography.body)
                .lineLimit(isExpanded ? nil : lineLimit)
                .animation(AnimationHelpers.easeInOut, value: isExpanded)
                .background(
                    // Hidden text to measure if truncation is needed
                    Text(text)
                        .font(LifeKBDesign.Typography.body)
                        .lineLimit(lineLimit)
                        .background(GeometryReader { geometry in
                            Color.clear.onAppear {
                                let fullTextHeight = text.boundingRect(
                                    with: CGSize(width: geometry.size.width, height: .greatestFiniteMagnitude),
                                    options: .usesLineFragmentOrigin,
                                    attributes: [.font: UIFont.preferredFont(forTextStyle: .body)],
                                    context: nil
                                ).height
                                
                                isTruncated = fullTextHeight > geometry.size.height
                            }
                        })
                        .hidden()
                )
            
            if isTruncated {
                Button(isExpanded ? "Show less" : "Show more") {
                    isExpanded.toggle()
                    AccessibilityHelper.selectionFeedback()
                }
                .font(LifeKBDesign.Typography.caption)
                .foregroundColor(LifeKBDesign.Colors.accent)
            }
        }
    }
} 